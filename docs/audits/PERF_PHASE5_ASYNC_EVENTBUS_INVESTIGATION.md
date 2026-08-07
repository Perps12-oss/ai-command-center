# Performance Investigation Report — Phase 5 Async EventBus

| Field | Value |
|-------|-------|
| **Date** | 2026-08-07 |
| **Authority** | `PERFORMANCE_CONSTITUTION.md` Art. VII / XII |
| **Status** | Approved for implementation |
| **Approval** | Human / cloud task: “COMPLETE … PHASE 5 … (async bus approved)” |
| **Program ownership** | Program 1 (Runtime) — EventBus |

---

## Problem

`EventBus.publish()` historically invoked every subscriber synchronously on the
publisher thread. Slow handlers (tools, workflows, LLM stream fan-out) delay
subsequent handlers and the publisher return path, amplifying UI freeze risk
when the publisher is the UI thread or a critical service path.

## Evidence

- Policy + RCA: `docs/architecture/ASYNC_EVENTBUS_POLICY.md`,
  `docs/audits/PERFORMANCE_RCA_UI_FREEZE_2026-07-24.md`
- Partial mitigation already on `main`: R4b single `event-dispatch` queue
  (`EVENTBUS_DISPATCH_QUEUE` / `async_dispatch=True` in `create_application`),
  R4c per-handler adapters — **missing** formal multi-pool
  `TieredDispatchPolicy` / `AsyncDispatchQueue` required by
  `PHASE_5_ASYNC_EVENTBUS_PLAN.md` exit criteria
- Truth matrix: Phase 5 row PARTIAL (`IMPLEMENTATION_TRUTH_MATRIX.md`)

## Call Chain

```text
Publisher (UI / service)
  → EventBus.publish(topic)
    → [sync] handler_1 … handler_N   # blocks publisher
    → [R4b optional] single queue → event-dispatch thread
```

Target chain (Phase 5):

```text
Publisher
  → EventBus.publish(topic)
    → TieredDispatchPolicy.classify(topic)
       → R4a IMMEDIATE: invoke inline (<5 ms budget)
       → R4b tool_execution pool (1 worker)
       → R4c workflow ThreadPool (4 workers)
       → R4d model queue (2 workers)
```

## Ownership

Program 1 Runtime owns EventBus, dispatch policy, and pool lifecycle.

## Root Cause

Single-threaded sync fan-out (and single shared async queue) does not isolate
tool / workflow / model workloads; Phase 5 plan deliverables for tiered pools
were never landed despite R4a–R4c hooks.

## Alternative Causes

- AppState notification storms (PERF-001) — mitigated separately; out of scope
- Inspector rebuilds (PERF-002) — out of scope
- Individual slow handlers — still require budgets; pools reduce publisher block

## Chosen Fix

Implement plan-named modules and wire EventBus:

1. `DispatchPolicy` ABC + `SyncDispatchPolicy` in `dispatch_policy.py`
2. `tiered_dispatch_policy.py` — R4a–R4d classification over existing topic tiers
3. `async_dispatch_queue.py` — bounded multi-pool workers + graceful shutdown
4. Feature flag `EVENTBUS_TIERED_DISPATCH` / `EventBus(tiered_dispatch=True)`
5. `create_application()` enables tiered dispatch (approval granted)
6. UCGS profile documents pool sizes; headless R4a p95 &lt; 50 ms gate test

**Non-changes (Art. X):** no `SYNC_CRITICAL` membership edits; bare `EventBus()`
stays sync; UI still must not touch Tk off main thread.

## Blast Radius

| Area | Impact |
|------|--------|
| EventBus | New optional path; existing single-queue path retained when tiered off |
| Services | No API change; handlers may run on pool threads when topic is ASYNC_ELIGIBLE |
| AppState / UI | SYNC_CRITICAL topics remain inline |
| Tests | `_drain_bus` uses aggregate `dispatch_queue_depth` |

## Success Criteria

| Criterion | Gate |
|-----------|------|
| Existing pytest suite green | CI |
| New tiered/queue/shutdown/isolation tests | CI |
| R4a publish→handler p95 &lt; 50 ms (synthetic) | CI (`test_r4a_dispatch_latency_p95`) |
| Arch lint + UCGS + constitution verify | CI |
| Docs: policy, plan exit, stop-line, truth matrix | This PR |

## Rollback

- `EventBus(tiered_dispatch=False)` / unset `EVENTBUS_TIERED_DISPATCH`
- Revert `create_application()` to `async_dispatch=True` only
- Full revert of Phase 5 modules if needed

## Out of bounds

- Enabling Goose / Predictive-Undo / OperatorKernel live wire
- Changing SYNC_CRITICAL topic set
- Claiming Windows ARM64 GUI soak from headless Linux
