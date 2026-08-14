# Gate Supersession Record — Workspace-Required Gate for `agent.*`

**Constitutional basis:** `PROJECT_CONSTITUTION_V4.md` Article VI (Gate Preservation) —
*"A gate may never silently disappear. Superseded gates must record: Replacement gate,
Reason, Date, Approval record."* Article VIII classifies this as a **feature change**, not a
refactor, because behaviour changes.

---

## Superseded gate

**Name:** Workspace-required admission gate, as applied to `agent.*` capabilities via
`UI_COMMAND`.

**Location at supersession:** `ai_command_center/services/execution_authority_service.py`
`_on_ui_command` (lines 200–213 at `59262fe` / `3709325`), keyed on
`_WORKSPACE_OPTIONAL_CAPABILITIES = frozenset({"navigate"})` (line 69).

**Behaviour before:** `analyze()` classified `"agent: demo"` as capability `agent.run`
(`:504-517`). `agent.run` was not workspace-optional, so with no active workspace the
command was deferred: `COMMAND_DEFERRED` + `UI_WORKSPACE_REQUIRED`, via the `INTENT_AGENT`
branch. The `AGENT_EXECUTION_REQUEST` intake applied **no** gate at all, so the same
capability was admitted or deferred depending solely on which intake it arrived through.

**Test coverage before:** none. `tests/test_program3_phase5.py:104-105` asserted deferral
only for `intent == "shell"`. No test asserted agent deferral, so removing this gate would
otherwise have passed CI silently.

---

## Replacement gate

**Name:** Capability-keyed workspace-required admission gate.

**Location:** `execution_authority_service.py` — `_workspace_optional(capability)` predicate
(single definition, Inv 11) consumed by `_admit(...)`, which every intake now calls:
`_on_ui_command`, `_on_workflow_execution_request`, `_on_agent_execution_request`.

**Behaviour after:** the gate is a pure function of capability and is applied identically by
every intake. `navigate`, `workflow`, and the `agent.*` family are workspace-optional; all
other capabilities still defer without an active workspace.

**The gate is extended, not weakened.** It now covers **two intakes that previously had no
gate at all** (`WORKFLOW_EXECUTION_REQUEST`, `AGENT_EXECUTION_REQUEST`). The net change in
coverage is an increase; the narrow reduction is that `agent.*` is now exempt on the UI path.

---

## Reason

1. **O-4 / Phase B requires decisional identity.** With the gate keyed on intake rather than
   capability, the same capability was treated differently by door — the precise defect the
   convergence exists to remove. Keying on capability is the only formulation under which
   "decisionally identical" is true.
2. **Preserving the old UI behaviour would have propagated the defect.** Retaining agent
   gating on `UI_COMMAND` while the `AGENT_EXECUTION_REQUEST` intake stayed ungated would
   have left the divergence in place under a different name.
3. **Agent runs do not require workspace scope to be correct.** They already ran ungated via
   `AGENT_EXECUTION_REQUEST` in production, and `AgentRuntimeService` plans carry their own
   `agent_id` / `spawn_role` scoping. Workspace context remains optional metadata on the
   `tool.invoke` envelope (`core/contracts.py` documented opt-out path 1).
4. **Phase A dependency.** Workspace-OS launches now enter via
   `WORKFLOW_EXECUTION_REQUEST`. A strict gate would defer them and reopen the very
   side-effect path Phase A closed.

---

## Consequence accepted

Typing `agent: <task>` with **no active workspace** no longer defers with
`UI_WORKSPACE_REQUIRED`; it proceeds to the agent plan. This is a deliberate,
user-visible behaviour change.

The `INTENT_AGENT` deferral branch in `_on_ui_command` became unreachable and was removed in
the same change; leaving it would have been a misleading remnant. `INTENT_AGENT` remains in
use for classification in `analyze()`.

---

## Verification

The replacement gate is covered by
`tests/test_intake_authority_convergence.py`:

| Test | Proves |
|------|--------|
| `test_agent_proceeds_without_active_workspace_on_every_intake` | The new behaviour, on **both** doors — pins the supersession so it cannot silently revert |
| `test_workflow_proceeds_without_active_workspace` | `workflow` exemption applied |
| `test_non_exempt_capability_still_defers_without_workspace` | Exemption is **not** over-broad — `shell` still defers |
| `test_all_intakes_emit_the_same_decision_field_set` | Decisional identity across all three intakes |

`tests/test_program3_phase5.py` (existing `shell` deferral) remains green — the gate it
asserts is intact.

---

## Approval record

| Field | Value |
|-------|-------|
| **Decision id** | B-D1a, option (A) — capability-keyed exemption + supersession record |
| **Approved by** | Repository owner, in-session, after the Phase B Boundary Review and Implementation Plan explicitly surfaced that B-D1 as worded removed an active gate |
| **Date** | 2026-08-11 |
| **Alternatives offered** | (B) intake-keyed exemption — zero regression, but no gate parity; (C) exempt `workflow` only and add gating to the agent intake — risked deferring programmatic agent runs |
| **Basis** | Phase B Boundary Review; `docs/audits/CONSTITUTIONAL_PRE_FLIGHT_PHASE_B_INTAKE_CONVERGENCE.md` §3 |
| **Supersedes** | Workspace-required gate for `agent.*` on `UI_COMMAND` (pre-Phase-B) |
| **Status** | ACTIVE |
