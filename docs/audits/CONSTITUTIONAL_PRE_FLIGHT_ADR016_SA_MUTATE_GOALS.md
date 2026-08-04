# Constitutional Pre-Flight — ADR-016 SA.mutate Goals (`submit_goal`)

**Date:** 2026-08-04  
**Branch:** `cursor/adr016-sa-mutate-goals-6855`  
**Baseline:** `origin/main` @ `e946d26` (#146 ADR-015 Memory mutate)

## Continuity

- ADR-015 Memory `store_memory` on `main`
- Stop line next gate: remaining non-WM SA.mutate domains (each needs ADR)
- This PR = **one combined gate**: ADR-016 + Goals-only mutate implementation

## Authority read

- [x] `PROJECT_CONSTITUTION_V4.md`
- [x] `STATE_AUTHORITY_CONTRACT.md` / ADR-015 / ADR-012 / ADR-006
- [x] `GOALS_DUAL_PATH_INVENTORY.md` / `SHADOW_SOT_INVENTORY.md`
- [x] `docs/audits/R1_UNGATED_STOP_LINE.md`

## Scope (in)

- ADR-016 Accepted: non-WM `SA.mutate` op = `submit_goal`
- `SingleGoalScheduler.submit_goal_for_state` → existing `submit_goal` (same SoT as intake)
- Inject `goal_submit` on SA; factory wire
- Receipt via `MutationReceipt.applied[]`; **never** write `GoalRepository` from SA directly
- **Hard rule:** no GoalEngine path; no WM dual-write of goals SoT
- Flip / add soft-shadow pins; update stop line / contract / inventory

## Out of scope (hard)

- pause / resume / cancel / status patch via SA
- Replacing UI/EA `GOAL_SUBMIT_REQUEST` intake (soft dual stays)
- Workflows / executions / agents mutate
- Memory delete; Async EventBus; Goose; Predictive/Undo live wire

## Dual-writer mitigation

| Forbidden | Required |
|-----------|----------|
| SA → `GoalRepository.save_goal` | SA → `goal_submit` → scheduler `submit_goal` |
| SA → GoalEngine | Same `goals` table + `GOAL_*` lifecycle as live intake |

## Architecture flow (enforced)

```text
Caller → SA.mutate(submit_goal) → SingleGoalScheduler.submit_goal_for_state
       → submit_goal → GoalRepository + GOAL_SUBMITTED (+ maybe activate/plan)
       → MutationReceipt (no WorldModel.apply for this op)
```

## Verdict

**GO**
