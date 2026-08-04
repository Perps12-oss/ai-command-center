# Executions Soft-Shadow Inventory (State Authority)

**Status:** ACTIVE — Stage 2 SHADOW step 6a (inventory + pins)  
**Authority:** `STATE_AUTHORITY_CONTRACT.md`, ADR-006, `SHADOW_SOT_INVENTORY.md` step 6  
**Date:** 2026-08-04  
**Baseline:** `origin/main` @ `96198bf` (#132)

## Verdict

Executions have an **append-only diagnostic SoT** (`execution_runs` /
`execution_events`) separate from the live orchestrator topic family and from
`workflow_runs`. State Authority does **not** aggregate or mutate executions
today. **Keep append-only.** **No silent-merge** with workflows or World Model.
**No `SA.mutate` for executions** in this slice.

| Path | Stack | On SA path? | Disposition |
|------|-------|:-----------:|-------------|
| **A — Diagnostic SoT** | `ExecutionRunService` / `ExecutionEventService` / `ExecutionQueryService` → repos → AppState hydration | ❌ | **keep** — append-only diagnostic truth |
| **B — Soft dual / adjacent** | Live `execution.run.*` orchestrator topics; workflow twin (`workflow_runs`); AppState feed; WM node type `execution_run` | ❌ | Document; correlate later via receipts; do not merge tables |

---

## Path A — Diagnostic SoT

```text
orchestration.run.snapshot / chat.complete / tool topics
  → ExecutionRunService → execution_runs (+ EXECUTION_RUNS_LOADED)
  → ExecutionEventService → execution_events (+ EXECUTION_EVENT_*)
  → ExecutionQueryService (read) → EXECUTION_QUERY_RESULT
  → AppState projections (library / timeline / inspector)
```

Evidence:

| Probe | Location |
|-------|----------|
| Run service | `services/execution_run_service.py` — `"execution_run"` |
| Event service | `services/execution_event_service.py` — `"execution_event"` |
| Query service | `services/execution_query_service.py` — `"execution_query"` |
| Repos | `ExecutionRunRepository`, `ExecutionEventRepository` |
| Factory | all three registered in `service_factory.py` |

---

## Path B — Soft dual / adjacent

| Surface | Role | Risk |
|---------|------|------|
| `ExecutionOrchestratorService` `execution.run.*` / `execution.step.*` | Live step pipeline | Soft — not the same as diagnostic tables |
| Workflow Persistence `workflow_runs` | Workflow-run SoT (5a) | Soft twin — **do not merge** with `execution_runs` |
| EA `_project_state` on workflow intake | WM/SA context only | Not execution SoT |
| AppState execution feed / library | Projection (R4) | Never authoritative |
| WM node type `execution_run` | Projection ranking in SA.query | Not `ExecutionRunRepository` |

---

## State Authority today

| Capability | Executions |
|------------|------------|
| `StateQuery` include flag | ❌ none |
| Factory lookup hook | ❌ none |
| `SA.mutate` | WM only — execution ops **unsupported** |

---

## Migration plan (ordered)

| Step | Action | Gate |
|------|--------|------|
| **6a ✅** | Publish this inventory + factory/SA pins | This PR |
| 6b | Correlate execution receipts with workflow/goal ids (docs + optional query fields) | Follow-up |
| 6c | Optional later: SA read-only project of recent runs — never dual-write | Contract R1 |
| ❌ | Silent-merge `execution_runs` ↔ `workflow_runs` ↔ WM | Forbidden |
| ❌ | `SA.mutate` for executions without ADR | Forbidden |

---

## Related shadow SoT

| Domain | Status |
|--------|--------|
| WM nodes/edges | ✅ SA mutate/query |
| Goals | ✅ ADR-012 A |
| Memory | ✅ 4a+4b (tools soft dual) |
| Workflows | ⚠️ 5a; 5b open |
| Executions | ⚠️ this document (6a) |

---

## References

- `docs/architecture/SHADOW_SOT_INVENTORY.md`  
- `docs/architecture/state_authority/WORKFLOWS_SOFT_SHADOW_INVENTORY.md`  
- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`  
- `ai_command_center/services/execution_run_service.py`  
- `ai_command_center/services/execution_event_service.py`  
- `ai_command_center/services/execution_query_service.py`  
- `ai_command_center/core/service_factory.py`  
