# Constitutional Pre-Flight — Stage 2 Slice 1 (State Authority Query)

**Date:** 2026-07-30  
**Branch:** `cursor/stage2-state-authority-query-6855`  
**Baseline:** `origin/main` @ `7f6e2ca`

## Authority documents read
- [x] `PROJECT_CONSTITUTION_V4.md`
- [x] `docs/architecture/STATE_AUTHORITY_CONTRACT.md`
- [x] `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`
- [x] `docs/architecture/adr/ADR-005_WORLD_MODEL_AUTHORITY.md`
- [x] `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md` (P3)
- [x] `docs/governance/IMPLEMENTATION_GUIDE.md`

## Scope (Slice 1 — mergeable)
1. Domain dataclasses: `StateQuery`, `StateProjection` (= `StateContext` v1), `ProjectionScope`, `StateDelta`, `MutationReceipt`
2. `StateAuthorityService.query()`; `project()` delegates to `query`
3. `mutate()` surface stub (NotImplemented — BrainRuntime interim documented)
4. Publish ownership table + SA event topics in contract (R1.3 partial)
5. Tests for `query`; keep migration tests green
6. Hygiene: mark Phase B rem / Stage 2 unblocked in Implementation Guide

## Out of scope
- Full `mutate()` unification / shadow-SoT kill
- GoalEngine merge
- Goose / Async EventBus
- OperatorKernel wiring (ADR-006)

## Architecture check
- UI never calls State Authority
- ExecutionAuthority remains sole intake
- World Model remains durable SoT (ADR-005); SA aggregates

## Verdict
**GO**
