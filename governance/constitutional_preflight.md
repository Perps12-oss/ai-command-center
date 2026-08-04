# Constitutional Pre-Flight — UI Freeze P1 (v6)

**Branch:** `cursor/ui-freeze-p1-budget-4fb7`  
**Authority:** PROJECT_CONSTITUTION_V4.md · PERFORMANCE_CONSTITUTION.md

## Intent

Reduce UI-thread starvation during chat streaming and event storms by budgeting
UIQueue drain work, phasing AppState→widget projection, throttling stream
appends, governing refresh rate, and deferring non-visible catalog rebuilds —
without changing user-visible behaviour or EventBus contracts.

## Invariants checked

| Invariant | Status |
|---|---|
| UI → AppState → EventBus → Services → Repositories → Storage | Preserved |
| UI isolation (no direct storage/Ollama/tools) | Preserved |
| No service-to-service calls | Preserved |
| Host supremacy | N/A |
| Contracts / topics | No topic or payload changes |

## Behaviour preservation

- Same EventBus topics and payloads
- Same navigation outcomes
- Same chat lifecycle (begin / stream / complete / cancel / error)
- Catalog views still refresh when visible or after deferred dirty apply
- `ACC_UI_FREEZE_FIX` bumped to `v6` for runtime fingerprint

## Risk

Medium — phased `_apply_state` and deferred catalogs must not drop lifecycle or
settings projection. Covered by UIQueue unit tests + state-applier unit tests +
existing shell projection tests.
