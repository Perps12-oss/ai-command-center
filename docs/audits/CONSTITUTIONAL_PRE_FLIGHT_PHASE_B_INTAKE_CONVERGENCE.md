# Constitutional Pre-Flight — Phase B: Intake Authority Convergence

**Status:** PRE-FLIGHT (written before implementation, per `CLAUDE.md` → Art. X)
**Baseline:** `3709325` (Phase A) on `feat/receipt-boundary-phase-a`; parent `59262fe`
**Scope:** B1 workflow convergence · B2 agent convergence · B3 decision-state isolation ·
B4 empty/invalid workflow completion · B5 record-only
**Owner decisions:** B-D1 APPROVE · B-D2 APPROVE · B-D3 DEFER · B-D4 APPROVE · B-D5 APPROVE
**Preceding review:** Phase B Boundary Review + Implementation Plan (read-only)

**Hard boundary set by owner:** Phase B is intake convergence and workflow lifecycle
correctness. It must **not** expand into general authority refactoring.

---

## 1. Authority read (Art. II order)

| Level | Document | Bearing |
|-------|----------|---------|
| 1 | `PROJECT_CONSTITUTION_V4.md` | Art. VI, VII, VIII decisive for B-D1a — see §3. Inv 4, 9, 11, 12 bear on B3/B4. |
| 2 | `AGENTS.md`, `docs/ARCHITECTURE_ENFORCEMENT.md` | ADR-018 sole `TOOL_INVOKE` publisher preserved; no service→service calls. |
| 3 | `docs/ARCHITECTURE.md`, contracts, topics | `EXECUTION_AUTHORITY_DECISION` payload extended additively only. |
| 4 | Accepted ADRs | **ADR-017 binding: workflows/executions/agents remain OUTSIDE StateAuthority mutate.** None amended. |
| 6 | Repository truth `origin/main` + Phase A | Evidence baseline in §2. |

Proposed ADR-007/009/011 remain non-binding.

---

## 2. Evidence baseline (verified by reading, not inference)

| Claim | Evidence |
|-------|----------|
| Workflow intake publishes no decision event, applies no gate | `services/execution_authority_service.py:263-326` vs `:177-261` |
| Agent intake has the identical divergence | `services/execution_authority_service.py:328-359` |
| Decision object *does* travel to scheduler | `:446` `authority_decision`; asserted `tests/test_execution_authority_hardening.py:200` |
| **UI agent commands are gated today** | `analyze()` → `agent.run` (`:504-517`); gate `:200-213`; `INTENT_AGENT` branch `:208-209`; `_WORKSPACE_OPTIONAL_CAPABILITIES = {"navigate"}` (`:69`) |
| Agent deferral is untested | `tests/test_program3_phase5.py:104-105` asserts `intent == "shell"` only |
| `"workflow:demo"` pollutes chat state | `core/state/chat_state.py:41-62` — no prefix match, not in exact list → `True` |
| Agent text also pollutes | `services/agent_runtime_service.py:319` `goal = task or f"agent:{agent_id}"` |
| `last_command` polluted unconditionally | `core/state/chat_state.py:72-77` (outside the pending filter) |
| Stuck-run defect is real | engine registers `_runs` `:106-112`, publishes `WORKFLOW_STARTED` `:120`, EA drops all steps and returns `:303-304` |
| Engine's existing failure gates are clean | `workflow_engine_service.py:85`, `:92` — both fire *before* `_runs` registration |
| No `WORKFLOW_FAILED` test coverage | `tests/test_workflow_engine_service.py` — 3 tests, none assert failure |
| Decision topic is `SYNC_CRITICAL` | `core/events/dispatch_policy.py:61` (5 ms budget) |
| Telemetry counts by source | `services/telemetry_summary.py:130` `bus_source == "execution_authority"` |

---

## 3. B-D1a — constitutional analysis (BLOCKING for B1/B2 gate work)

B-D1 approves adding `workflow` and `agent.*` to `_WORKSPACE_OPTIONAL_CAPABILITIES`.
Its stated rationale — *"forcing a workspace onto these paths would change established
behaviour"* — holds for `workflow`. It is **inverted** for `agent.*`: the gate is already
applied to UI agent commands today, so exempting them **removes** an active gate.

### This is not merely a behaviour change

**Article VI — Gate Preservation:** *"Passed gates become protected project contracts. A gate
may only be Extended, Replaced, or Superseded. A gate may never silently disappear.
Superseded gates must record: Replacement gate, Reason, Date, Approval record."*

**Article VIII — Refactor Governance:** *"If behavior changes: The work is a feature change.
Feature changes require full validation."*

**Article VII — Regression Policy:** budget ZERO; a task is incomplete if it *"breaks a gate"*
or *"weakens an invariant."*

Therefore option (A) is permissible **only** as a recorded gate supersession. It cannot be
implemented as an incidental line edit.

| Option | Constitutional status |
|--------|----------------------|
| **(A) Capability-keyed exemption** | Gate supersession (Art. VI) + feature change (Art. VIII). Requires a recorded supersession: replacement gate, reason, date, approval. Achieves true decision-identity — the gate becomes a function of capability, not of intake. |
| **(B) Intake-keyed exemption** | No gate removed; Art. VI/VII/VIII not engaged. Zero regression. But the same capability stays gated differently per door — B2 then delivers decision-event parity only, not gate parity. |

**Pre-flight recommendation:** proceed with **B3 and B4 now** (neither depends on B-D1a).
Obtain the B-D1a record before implementing the B1/B2 gate. If (A) is chosen, the
supersession record is a required deliverable of Phase B, not an afterthought.

The `INTENT_AGENT` deferral branch (`:208-209`) becomes dead code under (A) and must be
removed in the same change — leaving it would be a silent, misleading remnant.

**Implementation note (either option):** `_WORKSPACE_OPTIONAL_CAPABILITIES` is a `frozenset`
tested by exact `in`. Agent capabilities are `agent.run`, `agent.multi`, `agent.pipeline`,
`agent.shell`; a literal `"agent.*"` never matches. Requires a single predicate helper
(`_workspace_optional(capability)`) so the rule has exactly one definition — **Inv 11**.

---

## 4. Invariant analysis

| Invariant | Bearing | Assessment |
|-----------|---------|------------|
| **Inv 1** Ownership flow, no shortcut path | B5: `ui/controller.py:839` publishes `GOAL_SUBMIT_REQUEST` straight to the scheduler, bypassing EA | Recorded as a potential Inv-1 shortcut. **Investigate only** (B-D3 DEFER). Not acted on. |
| **Inv 4** AppState owns presentation; services own operational state | B3: authority decisions are *operational*; `chat_state` is *presentation* | Publishing operational decisions into chat presentation state **conflates the two**. B3 is directly required by Inv 4, not merely cosmetic. |
| **Inv 8** Topic governance | `EXECUTION_AUTHORITY_DECISION` payload gains an `intake` key | Additive; canonical topic unchanged. No consumer breaks on an extra key. |
| **Inv 9** Telemetry firewall | Decision volume rises; telemetry consumes it | Telemetry remains observe-only. No runtime behaviour keyed on telemetry. Compliant. |
| **Inv 11** Single authoritative owner | B4 restates EA's "executable step" filter in the engine | **Risk.** Must use one shared predicate, not two copies that can diverge. |
| **Inv 12** Non-circumvention | — | No wrapper/shim/compat layer introduced. |
| **ADR-017** | Workflows/executions/agents outside StateAuthority | No `SA.mutate` touched. Compliant. |

---

## 5. Planned changes (bounded)

**B4 — `services/workflow_engine_service.py`**
Pre-registration gate: if no step is a dict with `type == "tool"` and non-empty `tool`,
publish `WORKFLOW_FAILED` and return **before** registering `_runs` / publishing
`WORKFLOW_STARTED`. Fix sits in the engine because it owns workflow validation and the
`WORKFLOW_FAILED` idiom; putting workflow vocabulary in EA would violate ownership.
Shared step predicate to satisfy Inv 11.

**B3 — `services/execution_authority_service.py` + `core/state/chat_state.py`**
EA stamps `intake` provenance on the published decision payload.
`_reduce_authority_decision` returns `state` unchanged for non-`ui_command` intakes.
Rule: *publishing an authority decision must not mutate user-facing chat state unless the
decision represents an actual user chat command.*

**B1/B2 — `services/execution_authority_service.py` only**
Extract `_publish_decision(...)` and `_admit(...) -> bool` from `_on_ui_command:188-213`;
call from both other intakes before `_submit_plan`. **Gate semantics pending B-D1a.**
Workflow/agent are **not** routed through `analyze()` — they carry explicit tool manifests.

**B5 — record only.** No implementation.

---

## 6. Stop conditions

| # | Condition | Status |
|---|-----------|--------|
| 1 | Accepted ADR must change | NOT TRIGGERED |
| 2 | V4 / Art XIV required | NOT TRIGGERED — but **Art. VI supersession record required if B-D1a=(A)** |
| 3 | Dual execution authorities | NOT TRIGGERED — no new service |
| 4 | Proposed ADR treated as Accepted | NOT TRIGGERED |
| 5 | Historical evidence deleted | NOT TRIGGERED (dead `INTENT_AGENT` branch removal under (A) is a code remnant, not evidence) |
| 6 | Major WorkspaceOs/ActionRegistry redesign | NOT TRIGGERED — untouched |
| 7 | Scope expansion | NOT TRIGGERED — owner's hard boundary recorded §0 |
| 8 | UI-thread / Art XVII budgets | **WATCH** — `EXECUTION_AUTHORITY_DECISION` is `SYNC_CRITICAL`/5 ms; volume rises |
| 9 | Tests assert divergence as desired | NOT TRIGGERED — no test asserts the paths differ |
| 10 | O-1 re-interpreted | NOT TRIGGERED — no tier changes |
| 11 | `R1_UNGATED_STOP_LINE` hard stop | NOT TRIGGERED |

Additional halt: if B4's shared predicate cannot be expressed without EA importing workflow
vocabulary or the engine importing EA, stop and report rather than duplicating (Inv 11).

---

## 7. Verification plan

Per `CLAUDE.md` order: `verify_constitution.py` · `arch_lint.py --baseline` ·
`ruff check ai_command_center` · `pytest -m "not slow"` · `tests/test_receipt_coverage_gate.py`
must stay green (Phase A gate).

14 tests specified in the implementation plan, each labelled fails-today or passes-today.
Perf re-runs required due to decision volume: `test_appstate_reducer_performance.py`,
`test_perf_architecture.py`, `test_blueprint_performance.py`.

Known pre-existing failures on this host: `test_chat_message_height_c7`,
`test_program3_exit_gate` (tkinter/env; confirmed at `59262fe`).

---

## 8. Deliberately not touched

`core/workspace_os_actions.py` (FROZEN) · EventBus tiers (O-1) · StateAuthority / ADR-017 ·
`provider_sdk` (O-3) · `operator/`, `orchestration/execution|routing|policies` ·
OperatorKernel / GoalEngine / PlanningEngine / AgentCoordinator (ADR-006/012/013) ·
Predictive/Undo (ADR-014) · `analyze()` classification rules · Phase A receipt guard and
gate allowlist · B5 direct `GOAL_SUBMIT_REQUEST` implementation · general intake refactor.
