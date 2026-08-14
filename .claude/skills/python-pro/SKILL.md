---
name: python-pro
description: Use when writing or reviewing Python in ai-command-center — async correctness, type safety, and error handling under ACC constitutional invariants. Triggers on: new modules, refactors, async code, type annotations, exception handling, or ruff/mypy failures.
---

# Python Pro (ACC)

Idiomatic, typed, async-correct Python for `ai_command_center`.

## ACC governance deference

This skill is local tooling under `.claude/`. It is **not** Level-1/2 authority
(see `CLAUDE.md` → Authority). On conflict the higher authority always wins:

1. `PROJECT_CONSTITUTION_V4.md` (supreme)
2. `AGENTS.md`, `docs/ARCHITECTURE_ENFORCEMENT.md`
3. `docs/ARCHITECTURE.md`, contracts, topics
4. **Accepted** ADRs under `docs/architecture/adr/` (Proposed ≠ binding)
5. Repository truth on `origin/main`

Produce a Constitutional Pre-Flight under `docs/audits/` before implementing —
use `acc-preflight`. This skill never writes to
`docs/governance/IMPLEMENTATION_GUIDE.md`; Queue 1 is canonical there. If Queue 1
is EMPTY and the work is not otherwise approved, **stop and say so**.

## Invariants this skill will not help you violate

These have **no mechanical check** — you are the enforcement (`CLAUDE.md`):

- **No global state.** No `GLOBAL_MODEL`, `CURRENT_VAULT`, module-level mutable
  singletons, or import-time side effects. Pass dependencies explicitly.
- **All AI requests go through `ContextManager`** (Inv 6). Never call a provider
  SDK or raw `aiohttp`/`httpx` against a model endpoint directly.
- **Telemetry firewall** (Inv 9). No payloads, prompts, secrets, or user content
  into logs, spans, or metrics.
- **No deprecated import shims** and no wrapper/shim/migration path that dodges
  an existing gate (Inv 12, Art. IX).
- **Zero regression budget** (Art. VII).

## Type safety

- Annotate every public function, including `-> None`. Prefer precise types over
  `Any`; if `Any` is unavoidable, comment why.
- Use `from __future__ import annotations` for forward refs.
- Model domain data with `@dataclass(frozen=True, slots=True)` or `TypedDict`
  rather than loose dicts.
- Narrow with `typing.assert_never` in exhaustive `match`/`if` chains so new
  enum members fail type-check instead of falling through silently.
- `Protocol` over ABCs for structural seams — it keeps UI isolation testable
  without importing UI modules.

## Async correctness

- Never block the loop: no `time.sleep`, no sync `requests`, no blocking file
  or `keyring` calls inside a coroutine. Wrap blocking calls in
  `asyncio.to_thread(...)`.
- Prefer `async with` / `async for` over manual acquire-release.
- Reuse one `aiohttp.ClientSession` / `httpx.AsyncClient` per lifecycle owner;
  creating one per request leaks connections.
- Every `create_task` result must be retained and awaited or explicitly
  cancelled — bare fire-and-forget tasks get garbage-collected mid-flight.
- Lifecycle shutdown must use a **`.result()` timeout** (Art. XVII). Never
  `.result()` unbounded.

```python
async def shutdown(self, timeout: float = 5.0) -> None:
    self._stopping.set()
    for task in self._tasks:
        task.cancel()
    done, pending = await asyncio.wait(self._tasks, timeout=timeout)
    for task in pending:
        logger.warning("task did not stop within %.1fs: %r", timeout, task)
```

## Error handling

- Catch the narrowest exception that can actually be raised. Bare `except:` and
  broad `except Exception` without re-raise are review blockers.
- Never swallow `asyncio.CancelledError` — re-raise it after cleanup.
- Raise domain-specific exceptions at module boundaries; do not leak
  `aiohttp`/`httpx` exception types across an architectural seam.
- Log with `logger.exception(...)` inside the handler, not by formatting the
  traceback yourself. Log the *fact*, never the payload (telemetry firewall).

```python
try:
    result = await client.fetch(request_id)
except asyncio.CancelledError:
    raise
except httpx.TimeoutException as exc:
    raise ProviderTimeout(request_id) from exc
```

- Always use `raise ... from exc` so the cause survives.

## Verification

Cheapest-first, per `CLAUDE.md`:

```bash
python3 scripts/verify_constitution.py
python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json
python3 -m ruff check ai_command_center
python3 tools/ucgs_runner.py > .ucgs_last.yaml
python3 tools/ucgs_ci_gate.py .ucgs_last.yaml
APPDATA=/tmp/aicc_appdata python3 -m pytest -m "not slow"
```

Green ≠ approved. `.cursor` hooks and `tom-audit.yml` are advisory;
`TOM_APPROVAL.lock` is not CI-enforced. Independent verification is `acc-audit`.

## Environment

GUI is **Windows-ARM64 only**; `main.py` will not run on Linux x86_64. Headless
runs need `APPDATA` set. Verify product behaviour with `create_application()`
plus pytest, not the desktop GUI.
