# P1 Remediation Ledger

**Branch:** `cursor/p1-remediation-ucgs-efe6`  
**Date:** 2026-08-12  
**Evidence base:** `docs/audits/P1_NARROW_PASS_UCGS_SQLITE_EXECUTION.md` (+ Independent Verification conclusions restated there)

| Finding | Root cause | Changed files | Tests | Verification |
|---------|------------|---------------|-------|--------------|
| **P1-A** UCGS CI inert | `_collect_git_diff` only used `--cached` | `tools/ucgs_runner.py`, `.github/workflows/ucgs.yml`, `tools/install_git_hooks.py` | `tests/test_ucgs_diff_semantics.py` | `pytest tests/test_ucgs_diff_semantics.py`; CI range env + proof step |
| **P1-B** SQLite txn steal | Shared conn; unlocked writers; commit is connection-wide | `ai_command_center/db/conn_sync.py`, `connection.py` | `tests/test_sqlite_connection_threadsafe.py` | Steal regression + concurrent unlocked writers |
| **P1-C** ACTION_INVOKE bypass | `entity_bus_handlers` called `ActionRegistry.invoke` | `ai_command_center/core/entity/entity_bus_handlers.py` | `tests/test_p1_execution_permission_boundary.py` | No invoke; delegates `WORKFLOW_EXECUTION_REQUEST` |
| **P1-D** command permission hole | Only `tool=="shell"` checked | `ai_command_center/services/tool_executor_service.py` | same | `workspace_execute_command` denied without `LAUNCH_TOOL` |
| **EventBus** silent drop | `_enqueue` bool ignored; Full dropped all topics | `ai_command_center/core/event_bus.py`, `docs/architecture/ASYNC_EVENTBUS_POLICY.md` | `tests/test_eventbus_async_adapters.py` | `Event.delivery`; non-telemetry waits before drop |

## Intentionally not implemented (disproved)

- `id(conn)` instability as live P1
- alias→TOOL_INVOKE narrative
- reachable `drop_connection_lock` recursion

## Deferred (non-P1 / needs more product sequencing)

- Full EventBus drain-on-shutdown (policy future acceptance criteria)
- Exhaustive duplicate-implementation purge beyond verified competing authorities
- Broader ACC governance markdown-only rules (out of P1 scope)
