# Constitutional Pre-Flight — Phase 2+3 Adversarial Audit Remediation

**Date:** 2026-08-28
**Branch:** `cursor/phase2-audit-remediation-cf67`
**Authority:** `PROJECT_CONSTITUTION_V4.md`; `AGENTS.md`; `docs/ARCHITECTURE_ENFORCEMENT.md`;
`docs/ARCHITECTURE.md`; Inv 11 (single source of truth), Inv 12 (non-circumvention),
Art. XVII (UI budget / lifecycle), security_policy READ-tier contract
**Source finding set:** adversarial defect audit (2026-08-27) remaining items after Phase 1 (#201)

## Scope

Complete the remaining confirmed defects that Phase 1 explicitly deferred. No EventBus
architecture rewrite, no tier-table redesign, no orchestration executor rewire.

| Item | Defect | Change surface |
|------|--------|----------------|
| P2-A | B5 — deferred→replayed command loses `request_id` | `execution_authority_service.py` |
| P2-B | B6 — nested sync `ui.command` over SYNC_CRITICAL budget | `workspace_bootstrap_service.py`, `dispatch_policy.py` (async-eligible replay topic or deferred dispatch) |
| P2-C | Duplicate deferred-command idempotency | `workspace_bootstrap_service.py` |
| P2-D | B7 — `shell_readonly` `cat`/`type` unrestricted paths | `security_policy.py` and/or `command_sandbox.py` + `tool_executor_service.py` |
| P2-E | B8 — `ShellProvider` allows `git config` / `python <script>` | `command_sandbox.py`, `shell_provider.py` |
| P3-A | B9 — silent settings validation fallback | `settings_service.py` (+ optional `settings.error` topic) |
| P3-B | B14 — run snapshot / rehydration drops success attribution | `execution_run_service.py`, `app_state.py`, `domain/execution.py` as needed |

## Ownership boundaries preserved

- UI remains publisher/renderer; intake identity stays EventBus payload, not UI-held state.
- Security policy remains the READ-tier authority; sandbox enforces path/arg constraints.
- SettingsService remains the settings SoT; rejection is signaled, not shadowed.
- Execution run persistence remains repository-owned; rehydration must not invent success.

## Out of scope

- EventBus dispatch-policy redesign beyond marking a replay/deferral path async-eligible
- Cross-provider LLM fallback, model-existence checks
- Phase 1 items already shipping on #201

## Verification plan

- New/extended unit tests for each defect (audit §G items 6–12 plus B9/B14)
- `verify_constitution.py`, `arch_lint.py --baseline`, `ruff`, `ucgs_runner` + gate
- Targeted pytest for security sandbox, bootstrap idempotency/request_id, settings rejection, run rehydration
