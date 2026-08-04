# ADR-013: PlanningEngine & AgentCoordinator Live-Path Disposition

**Status:** Accepted — **remain research-only (not wired)**  
**Date:** 2026-08-04  
**Deciders:** Product / architecture (Stage 2 ungated closeout)  
**Does not supersede:** ADR-006 (ExecutionAuthority intake), ADR-012 (GoalEngine retire)  
**Related:** R1 Priority 2 composition registry, `IMPLEMENTATION_TRUTH_MATRIX.md`  
**Baseline:** `origin/main` @ `01ed04c`

---

## Context

R1.2 requires every composition-root row to be **keep**, **retire**, or **wire**. Two Phase-9 orchestration components still **exist-unwired**:

| Component | Live substitute already on `main` |
|-----------|-----------------------------------|
| `PlanningEngine` (`orchestration/goals/planning_engine.py`) | `PlannerService` (bus `PLAN_REQUEST`, SA-backed) |
| `AgentCoordinator` (`orchestration/agents/`) | `AgentRuntimeService` (factory-registered) |

Wiring them would create dual planners / dual agent authorities — the same class of split-brain ADR-006 and ADR-012 rejected for OperatorKernel and GoalEngine.

---

## Decision

**Accepted: PlanningEngine and AgentCoordinator remain research / unit-test only.**

Binding rules:

- Do **not** construct or register them in `service_factory` / application composition  
- Do **not** subscribe them to live intake or plan/agent topics that `PlannerService` / `AgentRuntimeService` already own  
- Promotion to live path requires a **new ADR** that demonstrates non-overlapping ownership and supersedes this decision  
- Tree may keep modules + unit tests until an optional cleanup PR  

Live composition remains:

```text
ExecutionAuthority → … → PlannerService / AgentRuntimeService → …
```

---

## Consequences

| Area | Effect |
|------|--------|
| R1.2 composition gate | **Closed** for these two rows |
| Truth matrix | PlanningEngine / AgentCoordinator = **RETIRED from live** (research tree) |
| P4 UI composition | Unblocked from this P2 item (P3 soft-shadow inventories also complete) |
| Phase 9 plan docs | Must not claim these are live-wired |

---

## Out of scope

- Deleting Phase-9 packages  
- Changing PlannerService / AgentRuntimeService contracts  
- Goose / Async EventBus  

---

## Verification

| Check | How |
|-------|-----|
| Not in factory | `build_services` has no PlanningEngine / AgentCoordinator construct |
| Live substitutes present | `planner` / `agent_runtime` in `ServiceManager.names()` |
| Matrix updated | This acceptance PR |

---

## References

- `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`  
- `docs/architecture/adr/ADR-012_GOALS_PHASE9_DISPOSITION.md`  
- `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md`  
- `ai_command_center/core/service_factory.py`  
- `ai_command_center/services/planner_service.py`  
- `ai_command_center/services/agent_runtime_service.py`  
