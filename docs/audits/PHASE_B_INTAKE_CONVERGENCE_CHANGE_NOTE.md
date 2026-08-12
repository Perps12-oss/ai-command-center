# Phase B — Intake Authority Convergence: What Changed / What Was Left Alone

**Baseline:** `3709325` (Phase A) on `feat/receipt-boundary-phase-a`
**Pre-flight:** `docs/audits/CONSTITUTIONAL_PRE_FLIGHT_PHASE_B_INTAKE_CONVERGENCE.md`
**Gate record:** `docs/audits/GATE_SUPERSESSION_WORKSPACE_REQUIRED_AGENT.md`
**Owner decisions:** B-D1 APPROVE · B-D1a **option (A)** · B-D2 APPROVE · B-D3 DEFER ·
B-D4 APPROVE · B-D5 APPROVE
**Owner boundary honoured:** intake convergence + workflow lifecycle correctness only; no
general authority refactoring.

---

## What the review changed about the work itself

The original B1 ("make WORKFLOW_START decisionally identical") was **not implemented as
scoped**, because the read-only review established three things the audit had not:

1. The decision *object* already travelled to the scheduler on every intake
   (`authority_decision` in `GOAL_SUBMIT_REQUEST`). Only the **event** and the **gate** were
   missing — so the runtime convergence was far smaller than the audit implied.
2. `AGENT_EXECUTION_REQUEST` had the **identical** divergence. Fixing only workflow would
   have moved the defect, not removed it.
3. B-D1 as worded **removed an active gate** rather than preserving behaviour, because
   `_on_ui_command` already gated `agent.*`. That made it an Article VI supersession.

---

## Code changes

| File | Change |
|------|--------|
| `core/contracts.py` | Added `is_executable_workflow_step()` — one owner for "what counts as a runnable workflow step" (Inv 11). Added `INTAKE_UI_COMMAND` / `INTAKE_WORKFLOW` / `INTAKE_AGENT` provenance constants. No version bumped. |
| `services/workflow_engine_service.py` | **B4:** reject a manifest with no executable tool step — publish `WORKFLOW_FAILED` and return **before** registering `_runs` / publishing `WORKFLOW_STARTED`. |
| `services/execution_authority_service.py` | **B1/B2:** extracted `_publish_decision(...)` and `_admit(...)`; both called by all three intakes. **B-D1a(A):** `_workspace_optional()` predicate; `workflow` + `agent.*` exempt. Dead `INTENT_AGENT` deferral branch removed. Step filter now uses the shared predicate. **B3:** decision payload carries `intake`. |
| `core/state/chat_state.py` | **B3:** `_reduce_authority_decision` returns state unchanged unless `intake == "ui_command"`. Missing `intake` is treated as a user command (backward compatible). |

### Why B4 lives in the engine, not ExecutionAuthority

The engine owns workflow validation and already owns the `WORKFLOW_FAILED` idiom. Having EA
publish workflow-domain events would duplicate ownership (Inv 11 / Art. V). The shared
predicate in `core/contracts.py` keeps EA's filter and the engine's gate from drifting — two
independent copies would silently reintroduce the stuck-run defect.

---

## Tests

`tests/test_workflow_step_validation.py` (B4) · `tests/test_decision_state_isolation.py` (B3) ·
`tests/test_intake_authority_convergence.py` (B1/B2) — 20 tests total.

| Behaviour | Proven failing before |
|-----------|----------------------|
| Non-executable workflow now fails explicitly | Yes — reproduced directly: baseline emitted `WORKFLOW_FAILED: 0`, `WORKFLOW_STARTED: 1`, orphaned `_runs: ['wf-x']` |
| Blank tool names fail explicitly | Yes |
| Workflow decision no longer touches chat state | Yes — guard removed → test fails |
| Agent decision no longer touches chat state | Yes |
| Workflow intake publishes a decision | Yes |
| Agent intake publishes a decision | Yes |
| **All three intakes emit the same field set** | Yes — the equivalence test whose absence let this survive |
| Agent admitted without workspace on both doors | Yes — pins the supersession |

Control tests that must keep passing (guard against over-correction): real chat commands
still populate chat state; a decision with no `intake` still behaves as before; `shell` still
defers without a workspace; mixed valid/invalid workflow steps still run.

**`"workflow:demo"` pollution was verified concretely,** not assumed: it matches none of
`_is_pending_chat_user_text`'s filtered prefixes and is not in the exact-match list, so it
returned `True` and became a pending user chat bubble. Agent text is worse — `goal = task or
f"agent:{agent_id}"`, so only the empty-task fallback was ever filtered.

---

## Verification

| Gate | Result |
|------|--------|
| `verify_constitution.py` | PASS |
| `arch_lint.py --baseline` | OK (4 baselined, no new) |
| `ruff check ai_command_center` | All checks passed |
| `pytest -m "not slow"` | **1384 passed**, 2 failed, 3 skipped |
| `tests/test_receipt_coverage_gate.py` (Phase A) | Green |

The 2 failures (`test_chat_message_height_c7`, `test_program3_exit_gate`) are **pre-existing
at `59262fe`** — confirmed during Phase A by re-running with source stashed. tkinter/env.

Perf checks re-run as planned (decision volume rose on a `SYNC_CRITICAL` topic):
`test_appstate_reducer_performance.py`, `test_perf_architecture.py`,
`test_blueprint_performance.py` — all green. Measured `workflow.start` warm cost after B4:
**0.024 ms** against a 10 ms budget; the shared predicate over 16 steps is **0.0009 ms**.
No Article XVII concern.

---

## Deliberate behaviour change (Article VI / VIII)

`agent: <task>` with no active workspace **no longer defers**. Recorded as a formal gate
supersession with replacement gate, reason, date, approval record and test coverage — see
`GATE_SUPERSESSION_WORKSPACE_REQUIRED_AGENT.md`.

Net gate coverage **increased**: the replacement gate now applies to two intakes that
previously had none.

---

## Deliberately left alone

- **B5 — direct `GOAL_SUBMIT_REQUEST` from Hero "New Goal"** (`ui/controller.py:839`).
  Recorded, not implemented (B-D3 DEFER). Potential Inv-1 shortcut and an authority
  provenance question; **not** a receipt-boundary defect — it is already receipted. Open
  question preserved: is `GOAL_SUBMIT_REQUEST` an internal post-authority command that must
  never be published externally, or a legitimate intake needing its own decision? Not assumed.
- `analyze()` classification rules — workflow/agent carry explicit tool manifests and are
  **not** routed through classification.
- `core/workspace_os_actions.py` (FROZEN, byte-identical since Phase A).
- EventBus tiers (O-1) · StateAuthority / ADR-017 (workflows/executions/agents stay outside
  `SA.mutate`) · `provider_sdk` (O-3) · `operator/` and the unwired paper stack ·
  OperatorKernel / GoalEngine / PlanningEngine / AgentCoordinator (ADR-006/012/013) ·
  Predictive/Undo (ADR-014) · Phase A receipt guard and gate allowlist.
- No ADR decision text amended. No V4 / Art. XIV amendment.

---

## Stop conditions — final assessment

| # | Condition | Status |
|---|-----------|--------|
| 1 | Accepted ADR must change | Respected |
| 2 | V4 / Art XIV required | Respected — Art. VI **record produced**, constitution unamended |
| 3 | Dual execution authorities | Respected — no new service |
| 4 | Proposed ADR treated as Accepted | Respected |
| 5 | Historical evidence deleted | Respected |
| 6 | Major WorkspaceOs/ActionRegistry redesign | Respected — untouched |
| 7 | Scope expansion | Respected — owner's hard boundary held; B5 recorded only |
| 8 | UI-thread / Art XVII budgets | Respected — measured, §Verification |
| 9 | Tests assert divergence as desired | Not triggered |
| 10 | O-1 re-interpreted | Respected — no tier changes |
| 11 | `R1_UNGATED_STOP_LINE` | Respected |

**No ADR-006 / 012 / 013 / 014 component was re-wired.**

---

## Phase B acceptance

- [x] B1 workflow authority convergence
- [x] B2 agent authority convergence
- [x] B3 decision-state isolation + regression tests
- [x] B4 no silent stuck runs — explicit failure and cleanup
- [x] B5 recorded as backlog, investigate-only
