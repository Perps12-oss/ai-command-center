# Constitutional Pre-Flight — Stage 2 Slice 4 (WM edges + Goals dual-path inventory)

**Date:** 2026-07-30  
**Branch:** `cursor/stage2-edges-goals-inventory-6855`  
**Baseline:** `origin/main` @ `77b4baa` (#126 merged)

## Authority documents read
- [x] `PROJECT_CONSTITUTION_V4.md`
- [x] `docs/architecture/STATE_AUTHORITY_CONTRACT.md` (R1 single access; R3 receipted mutate)
- [x] ADR-005 (World Model authority) / ADR-006 (ExecutionAuthority intake)
- [x] `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md` (R1.3 shadow SoT)
- [x] `docs/architecture/GOAL_ENGINE.md` (proposed contract — not live intake)

## Scope
1. Extend `StateAuthorityService.mutate` with WM edge ops: `create_edge` / `delete_edge`
2. Add `mutation_for_edge` helper alongside `mutation_for_node`
3. Publish Goals dual-path shadow-SoT inventory + migration plan (docs only — no GoalEngine intake merge)
4. Update contract, Implementation Guide, Truth Matrix, R1 plan

## Out of scope
- Merging `GoalEngine` into live `GOAL_SUBMIT_REQUEST` intake
- Wiring OperatorKernel / PlanningEngine / AgentCoordinator
- Goal / workflow / memory mutate via State Authority
- Goose / Phase 5 Async EventBus

## Architecture invariants preserved
- UI → AppState → EventBus → Services → Repositories → Storage
- Mutations remain receipted (`MutationReceipt`) and journaled via World Model
- ADR-006: ExecutionAuthority remains sole intake; GoalEngine stays off intake
- No silent dual-write of goals across `goals` and `goal_engine_goals` tables

## Verdict
**GO**
