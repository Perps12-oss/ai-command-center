# Audit Findings Closeout — 2026-08-28

| Field | Value |
|-------|-------|
| **Baseline** | `origin/main` @ `66be7de` (+ #201/#209) |
| **Branch** | `cursor/audit-findings-closeout-dfc2` |
| **Pre-flight** | `CONSTITUTIONAL_PRE_FLIGHT_AUDIT_FINDINGS_CLOSEOUT_2026-08-28.md` |

## Closed

| ID | Finding | Fix |
|----|---------|-----|
| P0 | Shell `communicate` on EventBus dispatch | `core/sandboxed_shell.py` + `ToolExecutorService` worker; tests use `ACC_TOOL_EXEC_INLINE=1` |
| P0 | SYNC_CRITICAL `ui.command` >5 ms | Post-admit `execution.dispatch.request` (ASYNC); light SA projection on sync intake. **MEASURED** avg ≈0.1 ms |
| P1 | Secrets plaintext / qwenpaw token | Fail-closed keyring store; qwenpaw keyring helpers; bus payload redaction |
| P1 | UI Rule 1 soft breaches | WorkflowIoService; launch via `UI_LAUNCH_RESOURCE`; SystemView projects `SYSTEM_SNAPSHOT` only |
| P2 | Duplicate shell | Shared `run_sandboxed_command` |
| P2 | `ActionRegistry.invoke` | Gated behind `ACC_ALLOW_ACTION_REGISTRY_INVOKE=1` |
| P2 | Stale docs | Diagram / ARCHITECTURE / RUNTIME_SAFETY aligned |
| P3 | CI perf floors | `test_perf_architecture` tightened (ui.command mean &lt;8 ms; reducer mean &lt;0.75 ms) |

## Explicitly not claimed Closed-DoD

- Win ARM64 GUI soak / freeze_fingerprint (host cannot run product GUI)
- God-file split of `app_state.py` / orchestrator (audit P3 debt; no drive-by)

## Evidence

- Focused pytest: receipt gate, secrets, perf, EA/orchestrator, closeout suite — green
- Headless `ui.command` budget remasured under Art IV after deferral
