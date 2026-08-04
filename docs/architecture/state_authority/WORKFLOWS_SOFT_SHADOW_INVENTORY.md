# Workflows Soft-Shadow Inventory (State Authority)

**Status:** ACTIVE — Stage 2 SHADOW step 5a (inventory + pins)  
**Authority:** `STATE_AUTHORITY_CONTRACT.md`, ADR-006, `SHADOW_SOT_INVENTORY.md` step 5  
**Date:** 2026-08-04  
**Baseline:** `origin/main` @ `e7732b9` (#130)

## Verdict

Workflows have a **clear live run path** and **no SA aggregation today**. Durable
SoT is `WorkflowRunRepository` via `WorkflowPersistenceService`. Adjacent
execution timeline / UI graph / frozen ABC are soft duals — **document, do not
silent-merge** into State Authority or World Model. **No `SA.mutate` for
workflows** in this slice. **Do not retire** `WorkflowEngineService`.

| Path | Stack | On SA path? | Disposition |
|------|-------|:-----------:|-------------|
| **A — Live run SoT** | `WORKFLOW_START` → `WorkflowEngineService` → lifecycle topics → `WorkflowPersistenceService` → `WorkflowRunRepository` (`workflow_runs`) → AppState | ❌ | **keep** — sole durable workflow-run SoT |
| **B — Soft dual / adjacent** | EA `project` (WM context only on intake); `ExecutionRunRepository` twin; UI `workflow_graph` / library; frozen `core/workflow/workflow_service.py` ABC | ❌ | Document; no silent merge; Engine stays |

---

## Path A — Live run SoT

```text
UI controller → WORKFLOW_START
  → WorkflowEngineService (in-memory _runs + status projector)
  → WORKFLOW_STARTED + WORKFLOW_EXECUTION_REQUEST
  → ExecutionAuthority → execution pipeline
  → execution.* → Engine mirrors workflow.step.* / completed / failed
  → WorkflowPersistenceService → WorkflowRunRepository
  → WORKFLOW_RUNS_LOADED / AppState.workflow_runs
```

Evidence:

| Probe | Location |
|-------|----------|
| Engine | `services/workflow_engine_service.py` — registered `"workflow_engine"` |
| Persistence | `services/workflow_persistence_service.py` — registered `"workflow_persistence"` |
| Repo | `repositories/workflow_run_repository.py` — table `workflow_runs` |
| Factory | both constructed + `services.register(...)` in `service_factory.py` |
| UI start | `ui/controller.py` publishes `WORKFLOW_START` |

---

## Path B — Soft dual / adjacent (not workflow-run SoT)

| Surface | Role | Risk if mistaken for SoT |
|---------|------|--------------------------|
| `ExecutionAuthority` + `_project_state` | WM/decision context when fulfilling `WORKFLOW_EXECUTION_REQUEST` | Medium — looks like SA owns workflows; it only projects WM |
| `ExecutionRunRepository` / execution timeline | Append-only execution twin | Soft — correlate later (SHADOW step 6); do not merge tables |
| AppState `workflow_graph` / library | UI projection (+ possible demo seed) | Projection only (R4) |
| `core/workflow/workflow_service.py` | Frozen ABC, **not** factory-wired | Paper path — ignore for live authority |

No capability tools named `workflow.*` found on the live path.

---

## State Authority today

| Capability | Workflows |
|------------|-----------|
| `StateQuery` include flag | ❌ none |
| Factory `workflow_lookup` | ❌ not wired |
| `SA.query` / `project` | WM + optional memory/goals only |
| `SA.mutate` | WM nodes/edges only — workflow ops **unsupported** |

---

## Migration plan (ordered)

| Step | Action | Gate |
|------|--------|------|
| **5a ✅** | Publish this inventory + factory/SA pins | This PR |
| 5b | Decide: add SA `project` hooks for run summaries **or** keep workflows execution-scoped outside SA | Human / follow-up |
| 5c | If hooks: read-only `workflow_lookup` → Persistence/repo (never Engine private `_runs`) | Contract R1 |
| ❌ | Silent-merge `workflow_runs` ↔ WM / execution_runs | Forbidden |
| ❌ | Kill WorkflowEngine or dual-write runs | Forbidden without ADR |

---

## Related shadow SoT

| Domain | Status |
|--------|--------|
| WM nodes/edges | ✅ SA mutate/query |
| Goals | ✅ scheduler; Phase-9 **RETIRED (ADR-012 A)** |
| Memory | ⚠️ soft dual — 4a inventory; 4b Assembler later |
| Workflows | ⚠️ this document (5a) |
| Executions | Soft append-only — SHADOW step 6 |

---

## References

- `docs/architecture/SHADOW_SOT_INVENTORY.md`  
- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`  
- `docs/architecture/state_authority/MEMORY_SOFT_SHADOW_INVENTORY.md`  
- `ai_command_center/services/workflow_engine_service.py`  
- `ai_command_center/services/workflow_persistence_service.py`  
- `ai_command_center/repositories/workflow_run_repository.py`  
- `ai_command_center/core/service_factory.py`  
- `ai_command_center/services/state_authority_service.py`  
