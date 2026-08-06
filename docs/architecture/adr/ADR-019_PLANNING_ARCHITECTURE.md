# ADR-019: Planning Architecture

**Status:** Accepted — B (Hybrid only for explicit replan events)  
**Date:** 2026-08-05  
**Deciders:** Multi-council Architecture Decision Framework  
**Related:** ADR-006, ADR-012, ADR-013, ADR-005, Phase 9 plan non-goals  
**Framework:** `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`  
**Baseline:** `origin/main` @ `631b1f3`

---

## 1. Problem Statement

Is **ReAct** the correct planning model for ACC?

A common fix for “script-runner agent” pain is to embed a ReAct loop (plan → act → observe → replan) inside `ExecutionOrchestratorService`, with WorldModel checkpoints and stuck-loop detection. ACC already has a BrainKernel FSM and a sequential orchestrator. Choosing ReAct as permanent architecture risks duplicating Brain, hiding loops, and converging on commodity agent runtimes.

---

## 2. Current Repository

| Fact | Evidence |
|------|----------|
| Live planner | `PlannerService` — deterministic/regex skeleton; publishes plans; does not execute — [`planner_service.py`](../../../ai_command_center/services/planner_service.py) |
| Live orchestrator | Sequential index over steps; approval pause; fail on tool error — [`execution_orchestrator_service.py`](../../../ai_command_center/services/execution_orchestrator_service.py) |
| BrainKernel FSM | BOOT / IDLE / PLANNING / EXECUTING / AWAITING_APPROVAL / … — [`brain_kernel_service.py`](../../../ai_command_center/services/brain_kernel_service.py), [`domain/kernel_state.py`](../../../ai_command_center/domain/kernel_state.py) |
| GoalEngine | **Retired** — ADR-012 |
| PlanningEngine / AgentCoordinator | **Research-only** — ADR-013 |
| ReAct | Phase 9 non-goals: autonomous ReAct loops rejected — `docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md` |
| Stuck-loop detector | Absent |
| World Model | Wired journal + apply via BrainRuntime — not used as orchestrator checkpoint today |

**Status:** Linear plan execution with approval gates. No ReAct loop on live path.

---

## 3. Independent Review Proposal

Replace the linear orchestrator with a ReAct state machine: PLANNING → EXECUTING → on failure REPLANNING (inject error + WM snapshot into planner) → STUCK if revised plans are near-duplicates (similarity &gt; ~0.9). Persist per-step checkpoints (tool, args, result, invariants) in World Model / SQLite. Escalate STUCK to human or stronger model.

---

## 4. Architect Council

**Defense of Proposal A (ReAct in orchestrator):**

- Conditional multi-step tasks collapse when step 2 returns unexpected data; linear plans cannot recover.
- Explicit WM checkpoints ground replanning in facts, not chat narrative.
- Stuck detection stops silent failure loops.
- ReAct is well-understood; engineering talent and papers map cleanly.
- Transforms “deterministic script runner wearing an agent costume” into a real agent loop.

---

## 5. Red Team

| Axis | Attack |
|------|--------|
| Assumptions | Assumes recovery belongs *inside* the orchestrator; BrainKernel already owns PLANNING/EXECUTING. |
| Scalability | Hidden loops + growing plan_history explode context; max-steps become ad hoc. |
| Uniqueness | Commodity ReAct agent — erodes Workspace OS / situation-driven Brain. |
| Maintainability | Duplicates Brain FSM; risks dual planners if PlanningEngine returns (ADR-013). |
| Production | STUCK→cloud model couples recovery to vendor (see ADR-023); approval path already exists. |
| Prior decisions | Phase 9 non-goal and ADR-013 already rejected this class of live dual planning. |

---

## 6. Alternative Architecture Team

**First principle:** Situation-driven control, not token-loop agents.

```text
Situation Engine (observations / AppState / WM)
        ↓
Goal Evaluation (scheduler / goal status)
        ↓
Execution (sequential orchestrator — one action at a time)
        ↓
Observe (receipts, tool results, errors)
        ↓
Update World Model (runtime-owned apply / journal)
        ↓
(explicit) plan.replan.request → PlannerService → new plan
```

- Orchestrator stays a **sequential executor**, not a thinking loop.
- Replan is an **explicit EventBus event** with WM snapshot payload — visible, testable, correlatable.
- Stuck = N near-identical plans via Planner/Brain → escalate through existing approval / Decision Record path (ADR-021).
- No nested ReAct costume inside ExecutionOrchestrator.

---

## 7. Systems Review Board

| Criteria | A ReAct orchestrator | B Situation → WM → explicit replan |
|----------|----------------------|-------------------------------------|
| Simplicity | 2 | 4 |
| Performance | 3 | 4 |
| Reliability | 3 | 4 |
| Local LLM | 3 | 4 |
| Testability | 2 | 5 |
| Extensibility | 3 | 5 |
| Uniqueness (Workspace OS) | 1 | 5 |
| Production Risk | 4 | 2 |

---

## 8. Constitution Guardian

| Question | Finding |
|----------|---------|
| More like every other assistant? | **A: Yes** — ReAct is the default agent blog-post architecture. |
| Erode Workspace OS? | **A: Yes** if Brain is bypassed; B strengthens situation/WM center. |
| Debt / dual authority? | **A: High** — orchestrator FSM vs BrainKernel. |
| Program separation? | A blurs Automation vs Intelligence ownership of “thinking.” |
| Temporary as permanent? | Stuck→stronger-model as escape hatch becomes permanent vendor dependency. |
| Inv 1–3 / 11 / 13? | B preserves EventBus-visible replan and single planner authority (ADR-013). |

Guardian **rejects A as primary**; allows Hybrid only as explicit bus-visible replan.

---

## 9. Council Decision

**Accept B**, with Hybrid only for **explicit replan events**:

1. Do **not** embed a ReAct loop inside `ExecutionOrchestratorService`.
2. Control loop is Situation → Goal Evaluation → Execution → Observe → Update World Model.
3. On failure: persist observation; publish structured replan request with WM snapshot; `PlannerService` owns revised plans.
4. Stuck detection compares plan revisions at Planner/Brain layer; escalate via approval / Decision Record — not silent retry.
5. Do not resurrect GoalEngine / PlanningEngine on live path without a new ADR superseding ADR-012/013.

---

## 10. Actionable Implementation Plan

| Milestone | Work | Tests / verification |
|-----------|------|----------------------|
| M1 | Define observation payload + WM/journal write on step success/failure from orchestrator (via runtime-owned apply path) | Unit + WM journal tests |
| M2 | Add EventBus topics e.g. `plan.replan.request` / `plan.replan.result` (names finalized in contracts); PlannerService handler builds revised plan from WM snapshot + error | Bus contract tests |
| M3 | Orchestrator on tool failure: emit replan request (bounded retries) instead of only `_fail_run`; remain sequential executor | Integration test multi-step fail→replan |
| M4 | Stuck detector: Jaccard/Levenshtein on last N plan serializations; on stuck → approval / Decision Record escalate | Unit tests for similarity thresholds |
| Out of scope | ReAct state machine inside orchestrator; cloud model as mandatory recovery brain | — |

**Dependencies:** ADR-018 intentions; ADR-005 WM authority; BrainKernel states.  
**Migration:** Extend existing services; no parallel PlanningEngine.

---

## References

- `docs/architecture/adr/ADR-012_GOALS_PHASE9_DISPOSITION.md`
- `docs/architecture/adr/ADR-013_PLANNING_AGENT_COORDINATOR_DISPOSITION.md`
- `docs/architecture/SYSTEM_STATE_AND_RECOVERY.md`
- `docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md`
- `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`
