# Constitutional Pre-Flight — execution scrubber ZeroDivisionError

**Branch:** `cursor/exec-scrubber-zerodiv-30d3`  
**Authority:** PROJECT_CONSTITUTION_V4.md

## Intent

Fix `ZeroDivisionError` in `ExecutionTimelineScrubber.set_timeline` when
`labels` has 0 or 1 entries: CustomTkinter's `CTkSlider.set` divides by
`number_of_steps`, and the scrubber previously configured `number_of_steps=0`.

## Invariants checked

| Invariant | Status |
|---|---|
| UI → AppState → EventBus → Services → Repositories → Storage | Preserved |
| UI isolation | Preserved — display widget only |
| No new EventBus topics | N/A |

## Behaviour preservation

- Multi-event scrubbing unchanged (`number_of_steps = count - 1`)
- Empty / single-event timelines show a safe disabled/degenerate slider

## Out of scope

- Executions view Phase 3 ~1.7s rebuild cost
