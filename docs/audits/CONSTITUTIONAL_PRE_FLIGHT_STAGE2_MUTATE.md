# Constitutional Pre-Flight — Stage 2 Slice 3 (StateAuthority.mutate)

**Date:** 2026-07-30  
**Branch:** `cursor/stage2-state-authority-mutate-6855`  
**Baseline:** `origin/main` @ `dab0dc7` (#123 merged)

## Authority documents read
- [x] `PROJECT_CONSTITUTION_V4.md`
- [x] `docs/architecture/STATE_AUTHORITY_CONTRACT.md` (R3 mutations receipted)
- [x] ADR-005 / ADR-006
- [x] `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md`

## Scope
- Implement `StateAuthorityService.mutate` for WM node ops: `create_node` / `update_node` / `upsert_node` / `delete_node`
- Return real `MutationReceipt`; publish `WORLD_MODEL_MUTATION_APPLIED`
- Thin reconstruction test: mutate → query without chat
- Document goals/workflows remain shadow SoT

## Out of scope
- Edge ops, GoalEngine merge, workflow SoT kill
- Routing mutate through BrainRuntime / RUNTIME_ACTION_REQUEST
- Goose / Async EventBus

## Verdict
**GO**
