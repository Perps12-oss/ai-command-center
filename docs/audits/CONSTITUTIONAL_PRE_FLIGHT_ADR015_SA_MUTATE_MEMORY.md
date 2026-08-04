# Constitutional Pre-Flight — ADR-015 SA.mutate Memory (`store_memory`)

**Date:** 2026-08-04  
**Branch:** `cursor/adr015-sa-mutate-memory-6855`  
**Baseline:** `origin/main` @ `7635585` (#145 R1 ungated docs closeout)

## Continuity

- Soft-shadow Stage 2 closed (3a–6b + agents)
- ADR-012 / 013 / 014 research-only dispositions on `main`
- Stop line next gate: **SA.mutate for non-WM domains — requires a new ADR**
- This PR = **one combined gate**: ADR-015 + Memory-only mutate implementation

## Authority read

- [x] `PROJECT_CONSTITUTION_V4.md`
- [x] `docs/architecture/STATE_AUTHORITY_CONTRACT.md`
- [x] `docs/architecture/SHADOW_SOT_INVENTORY.md`
- [x] `docs/architecture/state_authority/MEMORY_SOFT_SHADOW_INVENTORY.md`
- [x] ADR-005 / ADR-006 / ADR-012
- [x] `docs/audits/R1_UNGATED_STOP_LINE.md`

## Scope (in)

- ADR-015 Accepted: first non-WM `SA.mutate` op = `store_memory`
- Inject `memory_store` on `StateAuthorityService`; factory wire to `MemoryGraphService.store_memory`
- Receipt via `MutationReceipt.applied[]`; durable SoT remains `memory_nodes` (MGS)
- **Hard rule:** must not dual-write World Model memory nodes from this op
- Flip soft-shadow pin from "unsupported" → success + query round-trip
- Update contract / inventory / stop line / truth matrix honesty

## Out of scope (hard)

- Goals / workflows / executions / agents `SA.mutate`
- Memory delete / silent-merge `memory_nodes` ↔ WM
- Changing tool `memory.store` off capability path (may remain soft dual to same MGS)
- Async EventBus, Goose, OperatorKernel / Predictive-Undo live wire
- GoalEngine schema delete

## Why Memory first (not Goals)

Goals lifecycle is owned by `SingleGoalScheduler` + `GOAL_*` topics. SA writing
`GoalRepository` alone would risk dual-writer vs AppState. Memory already has
SA read (`memory_lookup`) and a single write owner (MGS) — lowest dual-writer risk.

## Architecture flow (enforced)

```text
Caller → SA.mutate(store_memory) → MemoryGraphService.store_memory
       → MemoryRepository (memory_nodes) → MEMORY_STORED → AppState
       → MutationReceipt (no WorldModel.apply)
```

## Verdict

**GO**
