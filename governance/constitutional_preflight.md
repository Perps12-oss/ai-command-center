# Constitutional Pre-Flight — Executions scrubber ZeroDivision + Phase 3 drain

**Branch:** `cursor/exec-scrubber-phase3-drain-4c3f`  
**Authority:** PROJECT_CONSTITUTION_V4.md + PERFORMANCE_CONSTITUTION.md  
**Evidence:** Operator logs — `CTkSlider` ZeroDivisionError in `set_timeline`; Phase 3 (executions view) 1390–1500 ms UIQueue drains

## Intent

1. **Correctness:** Guarantee `ExecutionTimelineScrubber.set_timeline` never configures
   `CTkSlider.number_of_steps=0` (CustomTkinter divides by steps in `set()`).
2. **Performance:** Stop identical Executions Center panel rebuilds (`clear_children` +
   CTk recreate) that dominate Phase 3 when the view is open — fingerprint child panels
   and gate scrubber projection to the executions view only.

## Invariants checked

| Invariant | Status |
|---|---|
| UI → AppState → EventBus → Services → Repositories → Storage | Preserved — renderer-only changes |
| UI isolation (no bus/service/storage in scrubber/panels) | Preserved |
| No global state | Preserved |
| No service-to-service calls | N/A |
| Host platform supremacy (Inv 13) | N/A |

## Behaviour preservation

- Scrubber still projects labels / index; empty and single-event timelines stay disabled
- Multi-event scrub still emits `on_scrub`
- ExecutionsView still applies all five panels when AppState fingerprint changes
- Scrubber live projection still uses `apply_timeline` when on Executions

## Out of scope

- PERF-001–005 register closeout / Win ARM64 soak
- Chat virtualization, EventBus async, SYNC_CRITICAL changes
- UI redesign of Execution Center layout
