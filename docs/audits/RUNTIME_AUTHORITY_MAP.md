# Runtime Authority Map

**Milestone:** PHASE R1 — Runtime Reconciliation  
**Baseline:** `origin/main` @ `e128a72`  
**Method:** Source + `service_factory.py` wiring only (not plan claims)

---

## Executive finding

The repository has **two authority stories**, not one:

| Story | Status on `main` |
|-------|------------------|
| **A — Execution Authority path** | **LIVE** (wired in factory, EventBus-driven) |
| **B — OperatorKernel path** | **PAPER** (library + tests; not in factory) |

Bridging gaps before choosing between A and B risks a **third bypass path**.

---

## A — Live authority path (verified)

```text
User / UI
    │
    ▼ UI_COMMAND
ExecutionAuthorityService          ← sole intake (ExecutionAuthorityService docstring)
    │  StateAuthorityService.project (before plan)
    ▼ GOAL_SUBMIT_REQUEST
SingleGoalScheduler              ← goal queue + persistence
    │
    ├─ synthetic plan (skip_planner) ──► PLAN_GENERATED (internal)
    │
    └─ else ──► PLAN_REQUEST ──► PlannerService ──► PLAN_GENERATED
    │
    ▼ EXECUTION_RUN_REQUEST
ExecutionOrchestratorService     ← step runner + approvals
    │
    ├─ LLM_STEP_REQUEST ──► ChatHandlerService ──► LLM_REQUEST / context
    ├─ CAPABILITY_RUNTIME_REQUEST ──► runtime / MCP providers
    └─ TOOL_INVOKE ──► ToolExecutor
    │
    ▼ EXECUTION_RUN_COMPLETE | FAILED
OrchestrationService             ← receipts, truth, orchestration snapshots
    │
    ▼ AppState projections ──► UI
```

### Evidence

| Step | File | Factory |
|------|------|---------|
| Intake | `services/execution_authority_service.py` | ✅ ~L268 |
| State projection | `services/state_authority_service.py` | ✅ ~L262 |
| Goal queue | `services/goal_scheduler_service.py` (`SingleGoalScheduler`) | ✅ ~L201 |
| Planning | `services/planner_service.py` | ✅ ~L206 |
| Execution | `services/execution_orchestrator_service.py` | ✅ ~L207 |
| LLM steps | `services/chat_handler_service.py` | ✅ ~L320 |
| Capability classify/map | `services/runtime_capability_router_service.py` | ✅ ~L238 |
| Completion / evidence | `services/orchestration_service.py` | ✅ ~L244 |

### Demoted / supporting (not intake)

| Service | Role today | Misleading if treated as authority |
|---------|------------|-----------------------------------|
| `CommandRouterService` | Workspace tracker + `classify()` facade | Doc: ExecutionAuthority owns intake |
| `RuntimeCapabilityRouterService` | Kind classifier + provider map | Dispatch only via orchestrator |
| `ChatHandlerService` | LLM/chat PlanStep handler | No user intake |
| `OrchestrationService` | Completion observer | Does not plan or execute steps |

---

## B — Paper authority path (Phase 8 plan, not wired)

```text
User
    ▼
OperatorKernel                    ← operator/kernel.py (tests only)
    ▼
PlanningEngine                    ← orchestration/goals/planning_engine.py (tests only)
    ▼
AgentCoordinator                  ← orchestration/agents/agent_coordinator.py (tests only)
    ▼
RuntimeCapabilityRouterService
    ▼
Provider / Tools
```

| Component | Exists | In `service_factory` | On live EventBus path |
|-----------|:------:|:--------------------:|:---------------------:|
| OperatorKernel | ✅ | ❌ | ❌ |
| PlanningEngine | ✅ | ❌ | ❌ |
| AgentCoordinator | ✅ | ❌ | ❌ |

`rg OperatorKernel` outside `operator/` → **tests only**.

---

## C — Parallel goal systems (consolidation risk)

| System | Wired | Notes |
|--------|:-----:|-------|
| `GoalEngine` + SQLite repo | ✅ | factory ~L200 |
| `SingleGoalScheduler` + Goal repo | ✅ | factory ~L201 |
| UI `GOAL_SUBMIT_REQUEST` | ✅ | ExecutionAuthority + Goal Dashboard |

Both goal engines coexist. R1 must decide whether they converge or divide responsibility explicitly.

---

## Decision gate (must answer before Priority 1 coding)

### Primary

> **Is the canonical authority path A (ExecutionAuthority chain) or B (OperatorKernel chain)?**

| Option | Implication |
|--------|-------------|
| **Adopt A as canonical** | OperatorKernel becomes internal library, adapter layer, or **retired**; docs/plans updated |
| **Migrate to B** | ExecutionAuthority intake delegates to OperatorKernel; large migration; must not leave dual intake |
| **Hybrid (explicit)** | Document which request classes use which kernel; forbidden: silent bypass |

### Secondary (only after primary)

1. Is `PlanningEngine` mandatory for all requests or goal-oriented only?  
   - Live: `PlannerService` on `PLAN_REQUEST`; synthetic plans skip it.  
2. Does `AgentCoordinator` sit under OperatorKernel or beside `AgentRuntimeService`?  
   - Live: `AgentRuntimeService` is wired; `AgentCoordinator` is not.  
3. What is the single execution graph diagram in `docs/ARCHITECTURE.md`?

---

## Anti-patterns to forbid in R1

```text
Component exists → not registered → not reachable → second shadow path
```

No new wiring until the decision gate is recorded in:

- `docs/ARCHITECTURE.md` (canonical graph)  
- `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md` (updated rows)  
- Constitution amendment if authority changes  

---

## Next artifact

Priority 1 deliverable after decision: **Runtime Authority Migration Plan** (events + services + retirement list) — implementation owned by Devin; Guardian verifies wiring matches chosen path.
