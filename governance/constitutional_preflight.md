# Constitutional Pre-Flight — ADR-007 / PERF-001 AppState notify coalesce

**Branch:** `cursor/adr007-perf001-appstate-30d3`  
**Authority:** PROJECT_CONSTITUTION_V4.md + PERFORMANCE_CONSTITUTION.md + ADR-007

## Intent

PERF-001 Phase 3 (single bottleneck): coalesce `chat.chunk` AppState listener
notifies to ≤25/s (40 ms window), with Investigation Report + before/after
headless metrics. Phase 2 `appstate.notify*` instrumentation already on main.

## Invariants checked

| Invariant | Status |
|---|---|
| UI → AppState → EventBus → Services → Repositories → Storage | Preserved |
| EventBus SYNC_CRITICAL membership | Unchanged (ADR stop) |
| EVENTBUS_DISPATCH_QUEUE / ASYNC_ADAPTERS defaults | Unchanged (ADR stop) |
| One bottleneck per PR | Yes — stream notify coalesce only |

## Behaviour preservation

- Reducers still apply every `chat.chunk` (state buffer stays complete)
- Non-stream topics still notify immediately
- UI stream path still receives coalesced refreshes via UIController → UIQueue
- `APPSTATE_NOTIFY_COALESCE_MS=0` disables coalesce (rollback)

## Out of scope

- PERF-002 inspector rebuilds, PERF-003 settings, PERF-004 navigation
- Dual EventCoordinator projection collapse
- Async EventBus (Phase 5)
