# Constitutional Pre-Flight — UI freeze side-quest closeout

**Branch:** `cursor/ui-freeze-sidequest-closeout-30d3`  
**Authority:** PROJECT_CONSTITUTION_V4.md

## Intent

Close the remaining UI-freeze side-quest items **before** the ADR-007 /
PERF-001 AppState notify gate:

1. Fail-loud `runtime_identity` (stdout+stderr + verify script + README triage)
2. Fingerprint-gate `ExecutionsView.apply_state` (user logs: Phase 3 ~1.7s)
3. Fingerprint-gate `CommandCenterView.apply_state` + dock/scrubber early-outs
4. Bucket list-panel durations so live seconds do not thrash row equality

## Invariants checked

| Invariant | Status |
|---|---|
| UI → AppState → EventBus → Services → Repositories → Storage | Preserved |
| UI isolation | Preserved — projection skips only |
| No new EventBus topics | N/A |
| Host platform supremacy (Inv 13) | N/A |

## Next gate (explicitly out of scope)

- ADR-007 Phase 3 AppState notification coalescing / PERF-001 soak
- Chat message virtualization for huge histories
- Dual EventCoordinator+AppState projection collapse (medium, separate)

## Behaviour preservation

- Panels still update when run/plan/orch/timeline identity changes
- Scrubber still works; dock skips only identical step fingerprints
