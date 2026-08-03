# Constitutional Pre-Flight — Stage 2 Slice 3 (Shadow SoT / Goals Dual-Path)

**Date:** 2026-07-30  
**Branch:** `cursor/stage2-shadow-sot-goals-f84f`  
**Baseline:** `origin/main` @ `dab0dc7` (#124 merged)

## Authority documents read
- [x] `PROJECT_CONSTITUTION_V4.md`
- [x] `docs/architecture/STATE_AUTHORITY_CONTRACT.md` (R1 single access; item 4)
- [x] `docs/architecture/adr/ADR-005_WORLD_MODEL_AUTHORITY.md`
- [x] `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`
- [x] `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md`
- [x] `docs/governance/IMPLEMENTATION_GUIDE.md`
- [x] `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`
- [x] `docs/audits/RUNTIME_AUTHORITY_MAP.md`

## Scope
- Publish shadow SoT inventory + per-domain migration plan
- Goals dual-path first: quarantine orphaned `GoalEngine` from live composition
- Correct truth matrix / runtime authority map (GoalEngine was overstated as WIRED live)
- Tests: factory does not wire GoalEngine; SA `goal_lookup` projects `GoalRepository`

## Out of scope
- `mutate()` unification (contract item 6)
- Domain merge of GoalEngine → SingleGoalScheduler models
- Memory / Workflow / Execution SA aggregation
- Goose / Async EventBus / reconstruction acceptance test (item 5)

## Ownership
```text
UI → AppState → EventBus → Services → Repositories → Storage
```
State Authority remains the only approved query path for planner/EA. Live goals SoT stays `GoalRepository` + `SingleGoalScheduler`.

## Verdict
**GO**
