# Constitutional Pre-Flight — UI Freeze v6 gap closure

**Branch:** `cursor/ui-freeze-v6-gaps-4fb7`  
**Authority:** PROJECT_CONSTITUTION_V4.md · PERFORMANCE_CONSTITUTION.md

## Intent

Close review gaps on freeze_fix=v6: terminal stream flush test coverage,
apples-to-apples `ui.apply_state` e2e metrics, single coalesce entry for
`_apply_state` shim, and documented off-catalog deferral policy.

## Invariants checked

| Invariant | Status |
|---|---|
| UI → AppState → EventBus → Services → Repositories → Storage | Preserved |
| UI isolation | Preserved |
| Contracts / topics | Unchanged |

## Behaviour preservation

- Stream throttle + terminal flush semantics unchanged (now tested)
- Catalog still refreshes on navigate-to-catalog via fingerprint
- `ui.apply_state` again measures phase1→phase3 wall time; phase3 is separate
