# Shadow Source-of-Truth Inventory

**Status:** ACTIVE — Stage 2 soft-shadow **ungated closeout complete** (3a–6b + agents)  
**Authority:** `docs/architecture/STATE_AUTHORITY_CONTRACT.md` (item 4)  
**Verified:** `main` @ `01ed04c`+ (2026-08-04)  
**Rule:** Exists ≠ Wired ≠ Authoritative. Transient caches are allowed; durable truth outside State Authority is not.

---

## Purpose

List every store or service that can be mistaken for authoritative workspace reality, classify it, and record the migration disposition. **Goals dual-path is first.**

---

## Inventory

| Domain | Owner today | Durable? | On SA path? | Shadow? | Disposition |
|--------|-------------|:--------:|:-----------:|:-------:|-------------|
| World Model | `WorldModel` + SQLite repo | ✅ | ✅ primary `query` | No | Keep — ADR-005 |
| Goals (live) | `GoalRepository` + `SingleGoalScheduler` | ✅ | ✅ `goal_lookup` read | Soft dual (was) | **Canonical live goals path** |
| Goals (Phase-9) | `GoalEngine` + `goal_engine_goals` | ✅ schema | ❌ | **Retired (ADR-012 A)** | Tree may remain for unit tests; **not** product SoT; cleanup optional |
| Memory | `MemoryGraphService` → `MemoryRepository` | ✅ | ✅ SA lookup + Assembler 4b | Soft tools | **4a–4c** — tools `memory.query` stay capability (not SA) |
| Executions | `ExecutionRun` / `ExecutionEvent` / `ExecutionQuery` → repos | ✅ append-only | ❌ | Soft | **6a+6b** — append-only; correlate via `correlation_id` |
| Workflows | `WorkflowEngine` + `WorkflowPersistence` → `WorkflowRunRepository` | ✅ | ❌ | Soft | **5a+5b** — keep execution-scoped outside SA |
| Agent runtime | `AgentRuntimeService` in-memory | ❌ | ❌ | Transient | Keep ephemeral; `AgentCoordinator` RETIRED-from-live (ADR-013) |
| Predictive / Undo packages | `PredictiveEngine` / `undo_replay.Timeline` | ❌ | ❌ | Research | **RETIRED from live (ADR-014)** — live = TimelineService / SnapshotService / WM recover |
| AppState / UI | reducers / views | ❌ | Projection | No | Never authoritative |

---

## Goals dual-path (detail)

### Live path (canonical)

```text
UI / ExecutionAuthority
  → GOAL_SUBMIT_REQUEST
  → SingleGoalScheduler
  → GoalRepository (SQLite `goals`)
  → PLAN_* / EXECUTION_RUN_*
  → AppState.brain_state.recent_goals
```

State Authority reads goals **only** via factory `_goal_lookup` → `goal_repo.list_goals()`.

### Orphan path (quarantined)

```text
GoalEngine + SQLiteGoalEngineRepository (`goal_engine_goals`)
  — constructed in factory historically
  — NOT registered on ServiceManager
  — NOT started by create_application
  — NO production create_goal / activate call sites
```

Different domain model (`orchestration.goals.goal.Goal` vs `domain.goal.Goal`) and status vocabulary. Silent merge is forbidden.

### Slice 3 action

Stop constructing `GoalEngine` / `SQLiteGoalEngineRepository` in `build_services()` so bootstrap no longer creates a parallel durable table or returns a live handle. Unit tests may still construct the Phase-9 stack directly. Research/opt-in wiring requires a future ADR + explicit factory flag.

---

## Migration plan (ordered)

| Step | Domain | Action | Gate |
|------|--------|--------|------|
| **3a ✅** | Goals | Inventory + quarantine GoalEngine from live composition | This doc + factory + tests |
| **3b ✅** | Goals | **ADR-012 Accepted — Option A (retire)** Phase-9 from product path | No live re-wire without new ADR; schema cleanup optional later |
| **4a ✅** | Memory | Soft-shadow inventory + SA lookup pins | `MEMORY_SOFT_SHADOW_INVENTORY.md` + tests |
| **4b ✅** | Memory | Assembler decision memory via SA `query` | `CapabilityContextAssembler.bind_state_authority` |
| **4c ✅** | Memory | Tool `memory.query` remains capability (not SA) | Doc honesty |
| **5a ✅** | Workflows | Soft-shadow inventory + factory/SA pins | `WORKFLOWS_SOFT_SHADOW_INVENTORY.md` + tests |
| **5b ✅** | Workflows | **Keep execution-scoped** — no SA workflow hooks | Closeout |
| **6a ✅** | Executions | Soft-shadow inventory; keep append-only | `EXECUTIONS_SOFT_SHADOW_INVENTORY.md` + tests |
| **6b ✅** | Executions | Correlate receipts via `correlation_id` / `get_by_correlation` | Closeout + pin |
| **Agents ✅** | Agents | Inventory + ADR-013 research-only PlanningEngine/AgentCoordinator | `AGENTS_SOFT_SHADOW_INVENTORY.md` |
| **7 ✅** | All | Reconstruction: mutate→recover→query (nodes+edges, no chat) | Contract item 5 |
| **8 ✅** | WM | Unify `mutate()` for nodes + edges with `MutationReceipt` | Contract item 6 (goals/workflows deferred) |

---

## Verification

| Check | How |
|-------|-----|
| GoalEngine not on live path | `build_services(...).goal_engine is None`; not in `ServiceManager` |
| Live goals via GoalRepository | SA `query(include_goals=True)` with `goal_lookup` |
| Truth matrix | GoalEngine = exists / not live-wired / retire-from-live-path |
| Bypass | Planner/UI must not import GoalEngine or GoalRepository |
| Workflows / executions off SA | no `_workflow_lookup` / `_execution_lookup`; 5b+6b docs |
| Agents | `agent_runtime` registered; no PlanningEngine/AgentCoordinator in factory |

---

## References

- `docs/architecture/adr/ADR-012_GOALS_PHASE9_DISPOSITION.md` ← **3b decision vehicle**
- `docs/architecture/adr/ADR-013_PLANNING_AGENT_COORDINATOR_DISPOSITION.md` ← **agents / R1.2**
- `docs/architecture/state_authority/GOALS_DUAL_PATH_INVENTORY.md`
- `docs/architecture/state_authority/MEMORY_SOFT_SHADOW_INVENTORY.md` ← **step 4**
- `docs/architecture/state_authority/WORKFLOWS_SOFT_SHADOW_INVENTORY.md` ← **step 5**
- `docs/architecture/state_authority/EXECUTIONS_SOFT_SHADOW_INVENTORY.md` ← **step 6**
- `docs/architecture/state_authority/AGENTS_SOFT_SHADOW_INVENTORY.md`
- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`
- `docs/audits/RUNTIME_AUTHORITY_MAP.md` §C
- `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`
- `ai_command_center/core/service_factory.py`
- `ai_command_center/services/goal_scheduler_service.py`
- `ai_command_center/services/memory_graph_service.py`
- `ai_command_center/orchestration/goals/goal_engine.py`
