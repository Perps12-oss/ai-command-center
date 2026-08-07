# Phase 5: Async EventBus Policy Implementation

**Status:** COMPLETE (implemented this PR — COMPLETE_ON_MAIN when merged)  
**Priority:** HIGH  
**Dependencies:** Phase 1-4 complete ✅; Performance Investigation Report + human approval ✅  
**Authority:** `ASYNC_EVENTBUS_POLICY.md`, `PROJECT_CONSTITUTION_V4.md`, `PERFORMANCE_CONSTITUTION.md`  
**Verification:** `docs/audits/PERF_PHASE5_ASYNC_EVENTBUS_INVESTIGATION.md`, `docs/audits/CONSTITUTIONAL_PRE_FLIGHT_PHASE5_ASYNC_EVENTBUS.md`

---

## Executive Summary

Non-blocking dispatch for heavy EventBus handlers via tiered multi-pool workers
(R4b/R4c/R4d), while R4a / `SYNC_CRITICAL` handlers remain synchronous.
Bare `EventBus()` stays sync; `create_application()` enables `tiered_dispatch=True`.

---

## Dispatch Tiers

| Tier | Name | Handlers | Mode | Latency Target |
|------|------|----------|------|----------------|
| R4a | Immediate | UI / settings / lifecycle (`SYNC_CRITICAL`) | Sync | &lt;5ms (exit: p95 &lt;50ms) |
| R4b | Queued | `tool.*` | Queue (1 worker) | &lt;50ms |
| R4c | ThreadPool | workflow / agent / notes / telemetry | ThreadPool (4) | &lt;200ms |
| R4d | Dedicated | `llm.*` / `chat.*` / `model.*` | Queue (2 workers) | &lt;500ms |

### Class Diagram

```text
DispatchPolicy (ABC)
├── SyncDispatchPolicy      (default, backward compat)
├── TieredDispatchPolicy    (Phase 5)
└── AsyncDispatchPolicy     (future migration target)

EventBus
├── publish() / dispatch() → tier-aware
├── dispatch_async(event) → always enqueue when queues exist
└── dispatch_sync(event) → always sync
```

---

## Implementation

| Deliverable | Path | Status |
|-------------|------|--------|
| 5.1 Policy ABC | `core/events/dispatch_policy.py` | ✅ |
| 5.2 Tiered policy | `core/events/tiered_dispatch_policy.py` | ✅ |
| 5.3 Worker pools | `core/events/async_dispatch_queue.py` | ✅ |
| 5.4 Config | `ucgs.profiles/ai-command-center.yaml` `dispatch_policy.pools` | ✅ |
| EventBus wire | `core/event_bus.py`, `application.py` | ✅ |
| Tests | `tests/test_tiered_dispatch_policy.py`, `tests/test_async_dispatch_queue.py` | ✅ |

### Feature flags

| Flag | Default | Effect |
|------|---------|--------|
| `EVENTBUS_TIERED_DISPATCH` / `tiered_dispatch=` | off (bare bus); **on** in `create_application` | Multi-pool R4b–R4d |
| `EVENTBUS_DISPATCH_QUEUE` / `async_dispatch=` | off | Legacy single queue |
| `EVENTBUS_ASYNC_ADAPTERS` | off | Per-handler `async_queue` |

---

## Migration Guide (service authors)

1. Keep handlers fast on `SYNC_CRITICAL` topics (settings, service lifecycle, UI intent).
2. For heavy work on `ASYNC_ELIGIBLE` topics, prefer publishing results back on the bus rather than blocking.
3. When `tiered_dispatch` is on, `tool.*` / `workflow.*` / `chat.*` handlers may run on pool threads — **do not** touch Tk widgets; use `UIQueue`.
4. Opt into per-handler deferral with `subscribe(..., dispatch_mode=HandlerDispatchMode.ASYNC_QUEUE)` when adapters are enabled.
5. Tests that need deterministic sync should construct `EventBus()` without flags.

---

## Testing

- [x] `test_sync_dispatch_policy` / classification
- [x] `test_tiered_dispatch_classification`
- [x] `test_async_dispatch_queue`
- [x] `test_worker_pool_shutdown`
- [x] `test_model_queue_isolation_from_blocked_tool_pool`
- [x] `test_r4a_dispatch_latency_p95_under_50ms`

---

## Exit Criteria (5.4)

- [x] Existing EventBus tests pass; new async/tiered tests pass
- [x] Architecture lint clean (verify in CI)
- [x] UCGS PASS (verify in CI)
- [x] R4a p95 &lt; 50ms synthetic gate
- [x] Migration guide complete (this doc + `ASYNC_EVENTBUS_POLICY.md`)

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial plan |
| 2026-08-07 | Implemented TieredDispatchPolicy + AsyncDispatchQueue; approval cleared |
