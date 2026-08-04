# ADR-016: State Authority Mutate — Goals (`submit_goal`)

**Status:** Accepted  
**Date:** 2026-08-04  
**Deciders:** Product / architecture (next hard gate after ADR-015)  
**Does not supersede:** ADR-005, ADR-006, ADR-012, ADR-015  
**Related:** `STATE_AUTHORITY_CONTRACT.md`, `GOALS_DUAL_PATH_INVENTORY.md` step 5  
**Baseline:** `origin/main` @ `e946d26`

---

## Context

ADR-015 opened non–World Model `SA.mutate` for Memory. Goals already have SA
**reads** (`goal_lookup` → `GoalRepository`) while writes go only through
`SingleGoalScheduler` (Path A; GoalEngine retired — ADR-012 A).

Naïve mutate designs dual-write:

| Approach | Problem |
|----------|---------|
| SA → `GoalRepository` directly | Scheduler queue / AppState diverge — **forbidden** |
| SA → publish `GOAL_SUBMIT_REQUEST` only | SA becomes intent broker without sync receipt |

The safe mirror of ADR-015 is a factory-injected callback into the **same**
scheduler write method that bus intake already uses.

---

## Decision

**Accepted: State Authority may mutate Goals via a single op `submit_goal`.**

Binding rules:

1. **Op shape**

   ```python
   {"op": "submit_goal", "title": "...", "description": optional,
    "priority": optional, "goal_id": optional}
   # workspace_id / correlation_id from StateDelta
   ```

2. **Sole durable write** goes through
   `SingleGoalScheduler.submit_goal_for_state` → `submit_goal` →
   `GoalRepository` / `goals` (+ `GOAL_SUBMITTED` and normal activate/plan cascade).

3. **Receipt:** `MutationReceipt.applied[]` includes at least `op`, `mutation_id`,
   `goal_id`, `title`, `status`, `workspace_id`.

4. **Hard forbid:** SA must **not** call `GoalRepository` directly, construct
   GoalEngine, or `WorldModel.apply` for this op as goals SoT.

5. **Still unsupported** without a further ADR: pause / resume / cancel /
   status patch; workflows / executions / agents mutate; memory delete.

6. **Intake soft dual:** UI / ExecutionAuthority may keep publishing
   `GOAL_SUBMIT_REQUEST`. SA mutate is an additional entry into the same
   `submit_goal` SoT (same pattern as tool `memory.store` vs ADR-015).

Live path:

```text
SA.mutate(submit_goal)
  → goal_submit callback (factory: SingleGoalScheduler.submit_goal_for_state)
  → submit_goal → goals table + GOAL_* lifecycle
  → MutationReceipt
```

**Cascade note:** submit may activate and emit `PLAN_REQUEST` when the scheduler
is idle — ownership stays with the scheduler; SA does not plan or execute.

---

## Consequences

| Area | Effect |
|------|--------|
| Contract | Goals mutate live via `submit_goal` |
| Inventory | Dual-path step 5 closed for submit-only |
| Stop line | Next = workflows / executions / agents mutate (each ADR) or memory-delete |
| Tests | Mutate → `query(include_goals=True)` round-trip; `create_goal` still unsupported |

---

## Out of scope

- Lifecycle ops via SA  
- Replacing ADR-006 bus intake  
- Workflows / executions / agents / memory-delete  

---

## Verification

| Check | How |
|-------|-----|
| Factory wire | `goal_submit=goal_scheduler.submit_goal_for_state` |
| Op supported | `submit_goal` in SA ops; no WM apply for it |
| Round-trip | mutate → SA.query finds goal title |
| Repo-direct | SA source has no GoalRepository import |
| Docs | Inventory / contract / stop line / matrix updated |

---

## References

- `docs/architecture/adr/ADR-012_GOALS_PHASE9_DISPOSITION.md`  
- `docs/architecture/adr/ADR-015_STATE_AUTHORITY_MUTATE_MEMORY.md`  
- `docs/architecture/state_authority/GOALS_DUAL_PATH_INVENTORY.md`  
- `ai_command_center/services/goal_scheduler_service.py`  
- `ai_command_center/services/state_authority_service.py`  
- `ai_command_center/core/service_factory.py`  
