# ADR-014: PredictiveEngine & UndoReplay Live-Path Disposition

**Status:** Accepted — **remain research-only (not wired)**  
**Date:** 2026-08-04  
**Deciders:** Product / architecture (R1 P5 inventory)  
**Does not supersede:** ADR-005 (World Model), ADR-006 (ExecutionAuthority), ADR-012, ADR-013  
**Related:** R1 Priority 5, `IMPLEMENTATION_TRUTH_MATRIX.md`  
**Baseline:** `origin/main` @ `7d1065b`

---

## Context

R1.2 deferred PredictiveEngine and UndoReplay to Priority 5. Both packages
**exist** under `core/world_model/` with unit tests, but:

| Component | Live substitute already on `main` |
|-----------|-----------------------------------|
| `PredictiveEngine` | BrainSituationPanel heuristics; SA / WM projections — no prediction bus |
| `undo_replay.Timeline` | `TimelineService` + `TIMELINE_UNDO_*` + `SnapshotService` + WM journal `recover` |

Wiring them would create dual undo / dual prediction authorities — the same
class of split-brain ADR-006/012/013 rejected for OperatorKernel, GoalEngine,
and PlanningEngine/AgentCoordinator.

Neither package has EventBus injection, durable repositories, or factory
registration today. UndoReplay’s `StateProvider.restore_*` would mutate outside
`StateAuthority.mutate`. PredictiveEngine still references Phase-9 goal/task
shapes, not the live `GoalRepository` / scheduler path (ADR-012).

---

## Decision

**Accepted: PredictiveEngine and UndoReplay remain research / unit-test only.**

Binding rules:

- Do **not** construct or register them in `service_factory` / application  
- Do **not** subscribe them to `timeline.*`, WM mutate, or Brain prediction UI topics  
- Do **not** feed Brain “Prediction / Blockers” from PredictiveEngine without a later ADR  
- Promotion to live path requires a **new ADR** proving non-overlapping ownership with TimelineService, SnapshotService, StateAuthority, and live goals  

Live adjacent paths remain:

```text
TimelineService / SnapshotService / WorldModel.recover → AppState → UI
BrainSituationPanel heuristics (not PredictiveEngine)
```

---

## Consequences

| Area | Effect |
|------|--------|
| R1 P5 wire | **Gated** on a future ADR — inventory closed |
| Truth matrix | PredictiveEngine / UndoReplay = **RETIRED from live** (research tree) |
| Package tree | May keep modules + unit tests until optional cleanup |

---

## Out of scope

- Deleting packages  
- Changing TimelineService / SnapshotService contracts  
- Async EventBus / Goose  

---

## Verification

| Check | How |
|-------|-----|
| Not in factory | `build_services` source has no PredictiveEngine / undo_replay construct |
| Live substitutes present | `timeline` / related services in composition as today |
| Matrix updated | This acceptance PR |

---

## References

- `docs/architecture/state_authority/PREDICTIVE_UNDO_INVENTORY.md`  
- `docs/architecture/adr/ADR-013_PLANNING_AGENT_COORDINATOR_DISPOSITION.md`  
- `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md`  
- `ai_command_center/core/world_model/predictive_engine/`  
- `ai_command_center/core/world_model/undo_replay/`  
- `ai_command_center/core/service_factory.py`  
