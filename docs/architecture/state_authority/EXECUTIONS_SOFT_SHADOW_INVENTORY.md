# Executions Soft-Shadow Inventory (State Authority)

**Status:** ACTIVE — Stage 2 SHADOW steps 6a+6b closed  
**Authority:** `STATE_AUTHORITY_CONTRACT.md`, ADR-006, `SHADOW_SOT_INVENTORY.md` step 6  
**Date:** 2026-08-04  
**Baseline:** `origin/main` @ `01ed04c` (#133)

## Verdict

Executions have an **append-only diagnostic SoT** (`execution_runs` /
`execution_events`) separate from the live orchestrator topic family and from
`workflow_runs`. State Authority does **not** aggregate or mutate executions
today. **Keep append-only.** **No silent-merge** with workflows or World Model.
**No `SA.mutate` for executions** in this slice.

**6b (Accepted):** Correlate receipts across domains via shared
`correlation_id`. The durable API is
`ExecutionRunRepository.get_by_correlation(correlation_id)`. Snapshots may
carry `goal_id` / `workflow_run_id` as payload fields — they are **not** FK
merges into those tables. No SA execution include flag.

| Path | Stack | On SA path? | Disposition |
|------|-------|:-----------:|-------------|
| **A — Diagnostic SoT** | `ExecutionRunService` / `ExecutionEventService` / `ExecutionQueryService` → repos → AppState hydration | ❌ | **keep** — append-only diagnostic truth |
| **B — Soft dual / adjacent** | Live `execution.run.*` orchestrator topics; workflow twin (`workflow_runs`); AppState feed; WM node type `execution_run` | ❌ | Document; correlate via `correlation_id`; do not merge tables |

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
| Correlation | `execution_runs.correlation_id` + `get_by_correlation` |

---

## Path B — Soft dual / adjacent

| Surface | Role | Risk |
|---------|------|------|
| `ExecutionOrchestratorService` `execution.run.*` / `execution.step.*` | Live step pipeline | Soft — not the same as diagnostic tables |
| Workflow Persistence `workflow_runs` | Workflow-run SoT (5a/5b) | Soft twin — **do not merge** with `execution_runs` |
| EA `_project_state` on workflow intake | WM/SA context only | Not execution SoT |
| AppState execution feed / library | Projection (R4) | Never authoritative |
| WM node type `execution_run` | Projection ranking in SA.query | Not `ExecutionRunRepository` |

---

## Receipt correlation (6b)

```text
same correlation_id
  → GoalRepository / operation index / execution_runs / (workflow payload)
  → ExecutionRunRepository.get_by_correlation(cid) → ordered runs
```

| Mechanism | Role |
|-----------|------|
| `CorrelationContext.correlation_id` | Cross-artifact link key |
| `ExecutionRunRepository.append(..., correlation=...)` | Persist on write |
| `ExecutionRunRepository.get_by_correlation` | Read correlated receipt set |
| Snapshot fields (`goal_id`, `workflow_run_id`, …) | Optional payload hints — not schema merge |

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
| **6a ✅** | Publish this inventory + factory/SA pins | #133 |
| **6b ✅** | Correlate execution receipts via `correlation_id` + pin test | Closeout PR |
| 6c | Optional later: SA read-only project of recent runs — never dual-write | Contract R1 |
| ❌ | Silent-merge `execution_runs` ↔ `workflow_runs` ↔ WM | Forbidden |
| ❌ | `SA.mutate` for executions without ADR | Forbidden |

---

## Related shadow SoT

| Domain | Status |
|--------|--------|
| WM nodes/edges | ✅ SA mutate/query |
| Goals | ✅ ADR-012 A |
| Memory | ✅ 4a+4b+4c |
| Workflows | ✅ 5a+5b |
| Executions | ✅ this document (6a+6b) |
| Agents | ✅ ADR-013 |

---

## References

- `docs/architecture/SHADOW_SOT_INVENTORY.md`  
- `docs/architecture/state_authority/WORKFLOWS_SOFT_SHADOW_INVENTORY.md`  
- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`  
- `ai_command_center/services/execution_run_service.py`  
- `ai_command_center/services/execution_event_service.py`  
- `ai_command_center/services/execution_query_service.py`  
- `ai_command_center/repositories/execution_run_repository.py`  
- `ai_command_center/core/service_factory.py`  
