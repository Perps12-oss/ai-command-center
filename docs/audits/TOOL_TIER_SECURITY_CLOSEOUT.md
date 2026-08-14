# Tool Tier Security Closeout

**Date:** 2026-08-13  
**Status:** COMPLETE — overturns `RUNTIME_INTEGRITY_CLOSEOUT.md` §4 "NO bypass found"  
**Supersedes:** PR #177 (`audit/agent-shell-falsification`) — provenance-based HITL was the wrong axis  
**Authority:** ADR-004 (SecurityTier + HITL), ADR-018 (sole `TOOL_INVOKE` publisher)

---

## Executive summary

Post-#176 closeout incorrectly concluded **no control-plane bypass remained**. Direct falsification and tier classification at the `TOOL_INVOKE` boundary proved otherwise. This closeout implements **Option (a): agents require approval for `WRITE_DESTROY` actions**, with SecurityTier as the authoritative HITL classifier.

---

## Architecture implemented

| Layer | Responsibility |
|-------|----------------|
| **SecurityTier** (`domain/runtime_safety.py`) | Policy / HITL decision (ADR-004) |
| **ToolSpec.tier** + **`core/security_policy.py`** | Authoritative classification; fallback table |
| **ExecutionOrchestrator** | Pauses `WRITE_DESTROY` steps; emits `tool.confirmation_required` |
| **ToolExecutorService** (`TOOL_INVOKE`) | Enforces tier resolution, rejects unclassified, requires `human_approved` for `WRITE_DESTROY` |
| **PermissionService** | Independent actor authorization (`LAUNCH_TOOL`) — not conflated with HITL |

**Fail-closed rules:**

- No resolvable tier → reject (`unclassified action rejected`)
- `WRITE_DESTROY` → HITL required **regardless of actor/provenance** (including workflow)
- `auto_approve` cannot suppress `WRITE_DESTROY` HITL
- Payload `actor_type=user` cannot escalate agent runs (unchanged from #175)

---

## Bypasses closed

| Bypass | Remediation |
|--------|-------------|
| `agent.*` capability label skipped HITL | `step_requires_human_approval` keys on **effective tool tier**, not capability prefix |
| HITL only for `ui` provenance | `WRITE_DESTROY` gates all provenances |
| `agent.task` → `UI_COMMAND` laundering | Orchestrator stamps `actor_provenance=agent`; EA `_ui_command_intake` de-escalates only |
| `python -m`, `git -c`, `--upload-pack`, alias injection | `CommandSandbox._ARG_DENYLIST` |
| Unclassified tools execute | `resolve_tool_tier` → `None` → `TOOL_FAILED` at boundary |
| Orchestrator capability-alias false denials | Classification at concrete tool name on `TOOL_INVOKE` |

---

## PR #177 supersession

#177 tightened provenance-based HITL (fail-closed vs UI-only gating). That was **safer than the original fail-open behavior** but keyed on the **wrong architectural axis** — capability labels and provenance are planner/authored and aliased (`create_note` → `notes.create`).

This implementation moves authoritative classification to:

1. `ToolSpec.tier` (declaration)
2. `security_policy.py` (fallback)
3. `TOOL_INVOKE` boundary (enforcement)

#177 was **not merged** and is **superseded** by this work.

---

## Parallel authority (parked — not merged)

`domain/execution_plan.py` defines `RiskTier` (LOW/MEDIUM/HIGH) with `capability_risk_for()` defaulting unknown capabilities to **MEDIUM** (fail-open). This serves the approval-center UI only.

**Governance item (Queue 2 / future ADR):** unify or formally separate `RiskTier` vs `SecurityTier` authorities. **Not in scope for this PR.**

---

## `shell_readonly`

Bounded READ tool using `READONLY_COMMAND_SANDBOX` — allowlist excludes `python` and `git`. `SecurityTier.READ` — no HITL. Verified: rejects `git status` and `python -m x`; permits `echo hi`.

---

## Verification

| Gate | Result |
|------|--------|
| `test_tool_tier_security_falsification.py` | adversarial suite |
| `test_control_plane_security_acceptance.py` | 19 tests |
| `pytest -m "not slow"` | full non-slow suite |
| `ruff`, `verify_constitution`, `arch_lint`, UCGS | required |

---

## Known pre-existing failures (not in scope)

- `test_chat_message_height_c7`
- `test_program3_exit_gate`

Baselined separately; not introduced by this closeout.
