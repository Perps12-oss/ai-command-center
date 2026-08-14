# P1 Remediation Ledger (complete)

**Branch:** `cursor/p1-remediation-ucgs-efe6`  
**Date:** 2026-08-12  
**Evidence:** `docs/audits/INDEPENDENT_VERIFICATION_AUDIT.md`, `docs/audits/P1_NARROW_PASS_UCGS_SQLITE_EXECUTION.md`

Disposition vocabulary: `FIXED` | `FIXED + REGRESSION TEST` | `JUSTIFIABLY DEFERRED`

| Finding | Disposition | Root cause | Changed files | Tests | Verification |
|---------|-------------|------------|---------------|-------|--------------|
| **P1-A** UCGS CI inert | **FIXED + REGRESSION TEST** | `--cached` only | `tools/ucgs_runner.py`, `.github/workflows/ucgs.yml`, `tools/install_git_hooks.py` | `tests/test_ucgs_diff_semantics.py` | Negative FAIL under `block`; CI permanent negative-proof step |
| **P1-B** SQLite txn steal | **FIXED + REGRESSION TEST** | Shared conn; commit connection-wide | `db/conn_sync.py`, `db/connection.py` | `tests/test_sqlite_connection_threadsafe.py` | Steal + unlocked concurrent writers |
| **P1-C** ACTION_INVOKE bypass | **FIXED + REGRESSION TEST** | `ActionRegistry.invoke` from bus handler | `core/entity/entity_bus_handlers.py` | `tests/test_p1_execution_permission_boundary.py` | invoke not called; workflow delegated |
| **P1-D** command permission hole | **FIXED + REGRESSION TEST** | shell-only gate | `services/tool_executor_service.py` | same | deny agent `workspace_execute_command` |
| EventBus silent drop / delivery | **FIXED + REGRESSION TEST** | enqueue bool ignored | `core/event_bus.py`, `ASYNC_EVENTBUS_POLICY.md` | `tests/test_eventbus_async_adapters.py` | `Event.delivery` |
| EventBus drain-on-shutdown | **FIXED + REGRESSION TEST** | worker exited on flag without draining | `core/event_bus.py`, policy docs | `test_shutdown_drains_queued_async_events` | queued work runs after shutdown signal |
| Orphan `event_bus/event.py` | **FIXED** | unimportable shadow of live `Event` | deleted `core/event_bus/event.py` | import/arch still OK | — |
| Dead `NotesRepository` twin | **FIXED** | unused competing class name | `repositories/notes_repository.py` → re-export | — | single SoT `NoteRepository` |
| Divergent `.windsurf` UI constitution | **FIXED** | Inv 11 duplicate | deleted `.windsurf/plans/UI_CONSTITUTION-ff006d.md` | — | — |
| Independent audit not in tree | **FIXED** | attachment-only | added `docs/audits/INDEPENDENT_VERIFICATION_AUDIT.md` | — | placement decision recorded |
| `id(conn)` instability | **JUSTIFIABLY DEFERRED** | disproved as live P1 | — | — | must not implement |
| alias→TOOL_INVOKE | **JUSTIFIABLY DEFERRED** | disproved | — | — | must not implement |
| drop-path recursion | **JUSTIFIABLY DEFERRED** | disproved / no callers | — | — | must not implement |
| Memory/Note wrapper vs db | **JUSTIFIABLY DEFERRED** | composition shims, not competing SoTs | — | — | P1: do not wholesale delete |
| GoalEngine / PlanningEngine trees | **JUSTIFIABLY DEFERRED** | ADR-gated research/quarantine | — | — | hard stops remain |
| Settings dual construct | **JUSTIFIABLY DEFERRED** | same repo SoT; not competing authority | — | — | optional later |

## UCGS permanent negative property

```text
bad PR diff → UCGS detects → FAIL → UCGS_ENFORCEMENT=block → CI cannot merge
```

Enforced by `tests/test_ucgs_diff_semantics.py` and the workflow step
**Permanent UCGS negative-proof gate**.
