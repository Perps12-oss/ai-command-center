# Final Remediation Report — P1 Track

**PR:** https://github.com/Perps12-oss/ai-command-center/pull/170  
**Branch:** `cursor/p1-remediation-ucgs-efe6`  
**Date:** 2026-08-12

## Executive Summary

Confirmed P1 blockers are fixed with regression tests: UCGS CI range-diff enforcement, SQLite transaction-bound connection guard, ACTION_INVOKE closed for direct ActionRegistry side effects, and `workspace_execute_command` under the same `LAUNCH_TOOL` gate as `shell`. EventBus publish delivery is now observable; non-telemetry queue Full waits before drop. Disproved Claude mechanisms were not implemented.

## P1 Remediation

### P1-A UCGS CI
- **Root cause:** staged-only `git diff --cached` in CI clean checkout  
- **Fix:** `UCGS_DIFF_MODE=range` + `UCGS_DIFF_BASE`/`HEAD` in workflow; staged remains local  
- **Tests:** `tests/test_ucgs_diff_semantics.py` (negative FAIL under block)  
- **Verification:** 7 passed locally; CI proof step asserts `diff_mode==range` with empty staged

### P1-B SQLite
- **Root cause:** shared connection; commit is connection-wide; unlocked writers  
- **Fix:** `GuardedConnection` from `connect()` retains lock while `in_transaction`  
- **Tests:** steal regression + unlocked-style concurrent writers  
- **Verification:** `tests/test_sqlite_connection_threadsafe.py` 5 passed

### P1-C ACTION_INVOKE
- **Root cause:** handler called `ActionRegistry.invoke` (OS side effects, no receipt)  
- **Fix:** delegate launches to `WORKFLOW_EXECUTION_REQUEST`; never invoke registry  
- **Tests:** `tests/test_p1_execution_permission_boundary.py`  
- **Verification:** invoke assert_not_called; workflow published

### P1-D Permission
- **Root cause:** gate only when `tool_name == "shell"`  
- **Fix:** frozenset `{shell, workspace_execute_command}`  
- **Tests:** deny/allow paths in same test module  
- **Verification:** passed

## Remaining Findings

| Item | Status |
|------|--------|
| EventBus delivery/backpressure observability | FIXED + TEST |
| EventBus full drain-on-shutdown | NOT FIXED — JUSTIFIED (policy future criteria; not a confirmed P1) |
| Bootstrap duplicate construction sweep | NOT FIXED — JUSTIFIED (no confirmed competing SoT in P1 evidence) |
| Broad duplicate-implementation purge | NOT FIXED — JUSTIFIED (reachability not confirmed for wholesale deletes) |
| `INDEPENDENT_VERIFICATION_AUDIT.md` file | Not in repo; used P1 narrow pass as authoritative restatement |
| Disproved id(conn)/alias/drop recursion | NOT FIXED — JUSTIFIED (must not implement) |

## Tests (local)

```text
pytest tests/test_ucgs_diff_semantics.py tests/test_sqlite_connection_threadsafe.py \
  tests/test_p1_execution_permission_boundary.py tests/test_eventbus_async_adapters.py \
  tests/test_receipt_coverage_gate.py tests/test_receipt_boundary.py \
  tests/test_workspace_os_walking_skeleton.py --no-cov
→ 43 passed
```

## Governance

```text
ruff check (touched modules) → pass
scripts/arch_lint.py --baseline → OK
```

## Runtime Verification

- UCGS: synthetic UI→OllamaService in range mode → FAIL + gate exit 1  
- SQLite: B blocked while A holds open txn; `A_PARTIAL` not durable; A rollback then B commits only `B_ONLY`  
- ACTION_INVOKE: registry.invoke not called  
- Permission: agent `workspace_execute_command` → permission denied

## Changed Files (by purpose)

- UCGS: `tools/ucgs_runner.py`, `tools/install_git_hooks.py`, `.github/workflows/ucgs.yml`, `tests/test_ucgs_diff_semantics.py`
- SQLite: `ai_command_center/db/conn_sync.py`, `connection.py`, `tests/test_sqlite_connection_threadsafe.py`
- Execution/auth: `entity_bus_handlers.py`, `tool_executor_service.py`, `tests/test_p1_execution_permission_boundary.py`
- EventBus: `event_bus.py`, `tests/test_eventbus_async_adapters.py`, `docs/architecture/ASYNC_EVENTBUS_POLICY.md`
- Docs: Pre-flight, ledger, P1 narrow status, ACC governance UCGS line

## Git / PR

- Branch `cursor/p1-remediation-ucgs-efe6`
- PR #170 (draft)

## Residual Risk

- CI must stay on `fetch-depth: 0` + range env or range mode fail-closes  
- Raw `sqlite3.connect` in some unit tests bypasses GuardedConnection (composition root is covered)  
- ACTION_INVOKE still accepts the topic for compatibility but only delegates launches  

## Final Status

```text
REMEDIATION PARTIALLY COMPLETE — BLOCKERS REMAIN
```

**Clarification:** Confirmed **P1 blockers are resolved**. Remaining items are non-P1 / deferred (shutdown drain, broad duplicate purge, absent independent-audit file in-tree). No unexplained P1.
