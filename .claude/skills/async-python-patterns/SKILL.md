---
name: async-python-patterns
description: Use for producer-consumer queues, concurrent async fan-out, backpressure, cancellation, and EventBus/UIQueue work in ai-command-center. Triggers on: asyncio.Queue, task groups, gather/TaskGroup, worker pools, throttling, or event dispatch changes.
---

# Async Python Patterns (ACC)

Concurrency patterns that hold under ACC's event-driven architecture.

## ACC governance deference

Local tooling under `.claude/` — **not** Level-1/2 authority (`CLAUDE.md` →
Authority). Higher authority wins on conflict:
`PROJECT_CONSTITUTION_V4.md` → `AGENTS.md` / `docs/ARCHITECTURE_ENFORCEMENT.md`
→ architecture + contracts → **Accepted** ADRs → `origin/main`.

Constitutional Pre-Flight under `docs/audits/` before implementing — use
`acc-preflight`. Never writes to `docs/governance/IMPLEMENTATION_GUIDE.md`
(canonical Queue 1). If Queue 1 is EMPTY and this is not approved work, stop.

## Hard stops — read before designing anything concurrent

From `docs/audits/R1_UNGATED_STOP_LINE.md`. These are **not** a backlog:

- **Phase 5 EventBus pool isolation → PARKED.** The R4b single-queue design is
  already live on `main` and the tiered-pool branch was abandoned. Do not
  reintroduce per-tier pools, priority lanes, or worker-class partitioning.
  `PERFORMANCE_CONSTITUTION.md` does **not** authorize it.
- **Re-wiring OperatorKernel / GoalEngine / PlanningEngine / AgentCoordinator →
  RETIRED.** Needs an ADR superseding 006/012/013. Do not restore.

If a concurrency problem seems to require either, that is an architecture
decision: stop and use `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`
(next free ADR is **ADR-024**).

## Structural invariants

- **UIQueue is event-driven. No polling loops at ≤100 ms** (Art. XVII). If you
  find yourself writing `while True: await asyncio.sleep(0.05)`, you want an
  `asyncio.Event` or a queue `get()`.
- **No service → service calls.** Services communicate through the bus.
- **ADR-018: `tool.invoke` is the sole publisher** for tool invocation.
- **UI isolation** is gated by `arch_lint`; do not import UI from services.
- **No global state** — queues, semaphores and sessions are owned by a
  lifecycle object, never module-level.

## Producer-consumer

Bounded queue for backpressure; unbounded queues turn a slow consumer into
unbounded memory growth.

```python
class Pipeline:
    def __init__(self, workers: int = 4, maxsize: int = 256) -> None:
        self._queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=maxsize)
        self._workers = workers
        self._tasks: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        self._tasks = [
            asyncio.create_task(self._worker(i), name=f"worker-{i}")
            for i in range(self._workers)
        ]

    async def _worker(self, index: int) -> None:
        while True:
            job = await self._queue.get()
            try:
                await self._handle(job)
            except asyncio.CancelledError:
                self._queue.task_done()
                raise
            except Exception:
                logger.exception("worker %d failed job %s", index, job.id)
            else:
                pass
            finally:
                self._queue.task_done()
```

`task_done()` belongs in `finally` — miss it once and `join()` hangs forever.

Drain, then cancel:

```python
async def stop(self, timeout: float = 5.0) -> None:
    try:
        await asyncio.wait_for(self._queue.join(), timeout)
    except TimeoutError:
        logger.warning("queue did not drain within %.1fs", timeout)
    for task in self._tasks:
        task.cancel()
    await asyncio.gather(*self._tasks, return_exceptions=True)
```

## Concurrent fan-out

Prefer `TaskGroup` (3.11+, and ACC documents Python 3.12) — it cancels siblings
on first failure and never silently drops exceptions:

```python
async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(fetch(url)) for url in urls]
results = [t.result() for t in tasks]
```

Use `gather(..., return_exceptions=True)` only when partial failure is genuinely
acceptable — and then you must inspect every result for `BaseException`.

Cap concurrency with a semaphore rather than slicing the input:

```python
sem = asyncio.Semaphore(8)

async def bounded(url: str) -> Response:
    async with sem:
        return await client.get(url)
```

## Cancellation

- Re-raise `CancelledError` after cleanup — swallowing it breaks shutdown.
- Use `asyncio.timeout()` over `wait_for` for nested deadlines.
- Cleanup that must survive cancellation goes in `finally` with
  `asyncio.shield` only if it is genuinely uninterruptible.

## Anti-patterns

| Don't | Do |
|---|---|
| `asyncio.sleep` polling loop | `asyncio.Event` / queue `get()` |
| Unbounded `Queue()` | `Queue(maxsize=N)` |
| Bare `create_task(...)` discarded | retain, await or cancel |
| `except Exception: pass` | narrow catch, log, re-raise |
| Per-request `ClientSession` | one session per lifecycle owner |
| Module-level queue/semaphore | owned by lifecycle object |

## Verification

`arch_lint` + `ucgs_runner` catch the gated seams; the polling rule, global
state and telemetry firewall are **manual**. Run the `CLAUDE.md` verification
order and route independent checking through `acc-audit`.
