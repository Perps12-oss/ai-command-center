# Runtime Authority Map

**STATUS:** LIVE verification artifact (intake = ExecutionAuthority). Not an implementation queue.

OperatorKernel path is **PAPER / RETIRED**. Do not restore it.

Canonical plan: [`docs/governance/IMPLEMENTATION_GUIDE.md`](../governance/IMPLEMENTATION_GUIDE.md)

**Milestone:** PHASE R1 — Runtime Reconciliation (**COMPLETE**)  
**Baseline:** `origin/main` @ `426c6b7` (map date); live path re-verified 2026-08-12 @ `b949f3e`  
**Method:** Source + `service_factory.py` wiring only (not plan claims)  
**Stop line:** [`R1_UNGATED_STOP_LINE.md`](R1_UNGATED_STOP_LINE.md)  
**Hygiene disposition:** [`REPO_STATE_HYGIENE_DISPOSITION_2026-08-07.md`](REPO_STATE_HYGIENE_DISPOSITION_2026-08-07.md)

---

## Executive finding

**Settled (ADR-006):** one live intake story. OperatorKernel / Phase-9 research
packages remain tests-only (ADR-012/013/014).

| Story | Status on `main` |
|-------|------------------|
| **A — Execution Authority path** | **LIVE** (wired in factory, EventBus-driven) — **canonical** |
| **B — OperatorKernel / research tree** | **PAPER** (library + tests; not in factory) |

Do **not** bridge A and B without an ADR that supersedes the retire decisions.
Bridging risks a **third bypass path**.

---

## A — Live authority path (verified)

```text
User / UI
    │
    ▼ UI_COMMAND   (incl. Hero New Goal → goal: <title>)
ExecutionAuthorityService          ← sole intake (ADR-006)
    │  EXECUTION_AUTHORITY_DECISION + StateAuthority.project + workspace gate
    ▼ GOAL_SUBMIT_REQUEST   (authority_decision stamped; EA only)
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
OperatorKernel                    ← operator/kernel.py (tests only; ADR-006)
    ▼
PlanningEngine                    ← orchestration/goals/planning_engine.py (tests only; ADR-013)
    ▼
AgentCoordinator                  ← orchestration/agents/agent_coordinator.py (tests only; ADR-013)
    ▼
RuntimeCapabilityRouterService
    ▼
Provider / Tools
```

| Component | Exists | In `service_factory` | On live EventBus path | Disposition |
|-----------|:------:|:--------------------:|:---------------------:|-------------|
| OperatorKernel | ✅ | ❌ | ❌ | Research-only (ADR-006) |
| PlanningEngine | ✅ | ❌ | ❌ | **RETIRED from live (ADR-013)** |
| AgentCoordinator | ✅ | ❌ | ❌ | **RETIRED from live (ADR-013)** |

`rg OperatorKernel` outside `operator/` → **tests only**.

---

## C — Parallel goal systems (consolidation risk)

| System | Wired | Notes |
|--------|:-----:|-------|
| `GoalEngine` + SQLite repo | ❌ | **RETIRED (ADR-012 A)** — not constructed in factory |
| `SingleGoalScheduler` + Goal repo | ✅ | **Canonical live goals path** |
| UI `GOAL_SUBMIT_REQUEST` | ❌ | **Removed (B5 fork 1)** — Hero publishes `UI_COMMAND`; only EA emits `GOAL_SUBMIT_REQUEST` |

Live durable goals SoT is `GoalRepository` only. Phase-9 `GoalEngine` remains in-tree for unit tests / future ADR; see `docs/architecture/SHADOW_SOT_INVENTORY.md`.

**Publisher audit (B5):** production `GOAL_SUBMIT_REQUEST` publishers are EA `_submit_plan` only. Hero/Goal Dashboard was the sole UI publisher and was re-routed; no other UI publisher found.

---

## Decision gate (must answer before Priority 1 coding)

### Primary — **RESOLVED 2026-07-21 (Answer A)**

> **Canonical authority path: ExecutionAuthority chain (A).**  
> Recorded in `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`.

| Option | Outcome |
|--------|---------|
| **A — ExecutionAuthority canonical** | ✅ **ACCEPTED** — evolve, do not replace |
| **B — OperatorKernel migration** | ❌ Rejected as authority path |
| **Hybrid without ADR** | ❌ Forbidden |

**OperatorKernel** is non-canonical until a future ADR supersedes ADR-006 with factory wiring + superiority proof.

### Secondary — **RESOLVED 2026-08-04 (R1 SA.mutate stop line)**

Stage 2 + ADR-015/016/017 closed the live State Authority mutate surface and
explicit non-mutate dispositions. See `R1_UNGATED_STOP_LINE.md`.

| Item | Outcome |
|------|---------|
| State Authority contract | ✅ Living — `STATE_AUTHORITY_CONTRACT.md` |
| Mandatory state projection before Planner | ✅ On live EA path |
| SA.mutate World Model nodes/edges | ✅ Live |
| SA.mutate `store_memory` | ✅ ADR-015 |
| SA.mutate `submit_goal` | ✅ ADR-016 |
| SA.mutate workflows / executions / agents | ❌ Explicitly **out** (ADR-017) |

No further R1-blocking SA.mutate deepen without a new ADR.

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

R1 runtime-authority decisioning is **closed** for the live EA path (ADR-006) and
the SA.mutate stop line (ADR-015–017). Do not open a parallel “Runtime Authority
Migration Plan” unless a new ADR supersedes 006 / 012 / 013 / 014 / 017.

Optional parallel hard stops (other tracks — not this map):

- Phase 5 Async EventBus (perf report + human approval)
- Goose Stage 3 + Integration Proposal + ADR
- Predictive/Undo live wire (ADR superseding ADR-014)
- Platform hotkey/tray live wire
