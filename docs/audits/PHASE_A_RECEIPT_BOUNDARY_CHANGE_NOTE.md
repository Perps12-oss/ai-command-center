# Phase A — Receipt Boundary: What Changed / What Was Left Alone

**Baseline:** `59262fe08e04f5c5d0a5348eb6a3f0a702293cc4`
**Branch:** `feat/receipt-boundary-phase-a`
**Pre-flight:** `docs/audits/CONSTITUTIONAL_PRE_FLIGHT_RECEIPT_BOUNDARY_PHASE_A.md`
**Scope:** A1, A2, A3 only. Phase B not started (per the prompt's gate).

---

## Correction to the audit (verified against code)

The audit listed "canonical runs succeeding before/without observer receipt" as a
HIGH ordering/race bypass. That is **not** accurate under `async_dispatch=True`.

`EXECUTION_RUN_COMPLETE` / `EXECUTION_RUN_FAILED` are in neither
`SYNC_CRITICAL_TOPICS` nor `ASYNC_ELIGIBLE_TOPICS`
(`core/events/dispatch_policy.py:47,66`), so `get_dispatch_tier` returns the
`SYNC_STANDARD` default and `EventBus.publish` takes the inline `_invoke_handlers`
branch (`core/event_bus.py:381-392`). Receipt emission and truth validation therefore
complete *before* `publish()` returns.

This mattered: it let the boundary be enforced synchronously with **no** async-tier
changes, keeping O-1 (no EventBus tier expansion) intact.

The real G1 defects were narrower and are both now fixed and covered by tests.

---

## Code changes

| File | Change |
|------|--------|
| `services/orchestration_service.py` | `_emit_completion` no longer returns early when `request_id`/`run_id` are absent. It synthesizes a correlation id and logs a warning, so a run can never complete with **no** receipt and **no** TruthBoundary validation. |
| `services/execution_orchestrator_service.py` | Subscribes to `ORCHESTRATION_RECEIPT` and records correlation ids. `_complete_run` now verifies a receipt exists for the run after publishing completion; if none does, it publishes `EXECUTION_RUN_FAILED` with `receipt_boundary_violation: True` and never lets the success stand. |
| `orchestration/workspace_launch_tools.py` (new) | Wraps the **frozen** launch handlers as `workspace_open_url` / `workspace_open_folder` / `workspace_execute_command` tools. Imports them rather than reimplementing (Inv 11 — single source of truth). |
| `services/tool_executor_service.py` | Registers the three workspace launch tools as builtins. |
| `core/workspace_os_service.py` | `_on_launch_resource` publishes `WORKFLOW_EXECUTION_REQUEST` (an existing ExecutionAuthority intake) with an explicit tool step instead of `ACTION_INVOKE_REQUEST`. Launches now enter the canonical boundary. |

### Why "publish complete, then fail closed" is sound

The guard publishes `EXECUTION_RUN_COMPLETE` and only then verifies. That is safe
because the *only* component that turns `EXECUTION_RUN_COMPLETE` into user-visible
success is `OrchestrationService` — and it is exactly the component whose absence or
failure triggers the violation. In the violation case nothing user-facing was emitted
from the completion; the follow-on `EXECUTION_RUN_FAILED` produces the failure
response. **The user never observes a success that lacks a receipt.**

---

## Tests

`tests/test_receipt_boundary.py` (new)

| Test | Fails at baseline? |
|------|--------------------|
| `test_run_without_receipt_observer_fails_closed` | **Yes** — baseline reported success with no receipt |
| `test_completion_without_correlation_id_still_receipts` | **Yes** — baseline early-returned, emitting nothing |
| `test_workspace_os_launch_is_receipted` | **Yes** — baseline launched via ActionRegistry, unreceipted |
| `test_run_with_receipt_observer_succeeds_and_is_receipted` | No — control test for the already-working path |
| `test_reused_request_id_does_not_inherit_a_stale_receipt` | N/A — guards a defect introduced by this work (see below) |

**On the stale-receipt guard.** The receipt ledger is cleared both before the
completion publish and after the guard reads it. Mutation testing showed either clear
alone is sufficient; the test fails only when **both** are removed. They are kept as
defense-in-depth, and the clear also bounds ledger growth for failure receipts. This is
stated precisely because a single-clear mutation does *not* fail the test — the coverage
is of the invariant ("a reused id must not inherit earlier evidence"), not of one line.

`tests/test_receipt_coverage_gate.py` (new, A3) — enumerative AST scan:

- `test_every_side_effect_site_is_bounded_or_allowlisted` — every `subprocess.*`,
  `os.startfile`, `webbrowser.open` site must be inside the boundary or on a
  severity-annotated allowlist. **Verified it fails** on an injected new bypass.
- `test_gate_actually_sees_the_known_side_effects` — guards against a broken walker
  silently matching nothing.
- `test_no_action_registry_launch_bypass` — no production module may publish
  `ACTION_INVOKE_REQUEST`, locking the G2 route shut.

AST is used rather than regex specifically so a docstring mentioning
`subprocess.run` is not mistaken for a call.

`tests/test_execution_orchestrator_service.py` — two tests now compose the real
`OrchestrationService`. They previously drove runs to completion with no receipt
observer; under the new contract that is itself the bypass. They did **not** assert
bypass-without-receipt as *desired* behaviour, so stop condition 9 was not triggered.

---

## Verification

| Gate | Result |
|------|--------|
| `verify_constitution.py` | PASS |
| `arch_lint.py --baseline` | OK (4 baselined, no new) |
| `ruff check ai_command_center` | All checks passed |
| `pytest -m "not slow"` | 1368 passed, 2 failed, 3 skipped |

The 2 failures (`test_chat_message_height_c7`, `test_program3_exit_gate`) are
**pre-existing at `59262fe`** — confirmed by re-running them with the source changes
stashed. Both are tkinter/environment related on this host.

---

## Deliberately left alone

- **`core/workspace_os_actions.py` — byte-identical.** Its FROZEN header would have
  required a constitutional amendment. The re-route lives in `workspace_os_service.py`,
  which carries no freeze marker, so stop conditions 2 and 6 were not triggered.
- **ActionRegistry — unchanged, and given no execution authority.** It sits *below*
  `TOOL_INVOKE`, the same position `ToolExecutorService` occupies. ADR-018's sole-publisher
  rule is intact: `ExecutionOrchestratorService` remains the only `TOOL_INVOKE` publisher.
- **EventBus tiers — untouched** (O-1). The design deliberately avoids needing them.
- **`provider_sdk/` and unused adapters — dormant** (O-3).
- **`operator/`, `orchestration/execution|routing|policies`** — still unwired paper stack.
- **External / `mcp.*` weak handlers** (G7) — allowlisted, Goose Stage 3 gated.
- **Chat export, Runtime Inspector, QwenPaw sidecar** — allowlisted with severity, not
  fixed; the audit placed them outside Phase A.
- **No ADR text amended; no historical evidence or dead code deleted.**

---

## Known behavioural change (flagged for owner)

`_on_launch_resource` previously called `_await_result`, which is **not** blocking — it
pops a dict populated by synchronous dispatch (`workspace_os_service.py:227-229`). Because
`TOOL_INVOKE` is `ASYNC_ELIGIBLE`, launch results are no longer available synchronously.

**Consequence:** launch failures no longer raise `ValueError` synchronously from the UI
handler; they surface through the receipt / truth / `CHAT_COMPLETE` path instead.

This is the direct consequence of bringing the path inside the boundary and is the
behaviour the prompt asked for ("obtain receipts, or fail closed"). No UI caller depended
on catching that exception (`ui/workspace_os_controller.py` publishes and returns).

---

## Hand-off to Phase B (B1 / O-4)

`ExecutionAuthorityService._on_workflow_execution_request` diverges from
`_on_ui_command`: it publishes **no** `EXECUTION_AUTHORITY_DECISION` and applies **no**
workspace-required gate. That is precisely the O-4 divergence B1 must converge.

**A2 now routes workspace launches through that same intake**, so B1 has a second
consumer to keep working when it converges the semantics. This was the minimal seam that
avoided inventing a new authority path; it is called out here so the Phase B implementer
does not discover it by surprise.

Also noted for B1: `RESOURCE_TYPE_FILE` ("file") is not in the launch mapping and falls
through to `workspace_open_url`. This **matches baseline behaviour** exactly (the old
code defaulted unknown types to "Launch URL" too), so it is not a regression — but it is
latent oddness worth resolving deliberately rather than by default.

---

## Stop conditions — final assessment

| # | Condition | Status |
|---|-----------|--------|
| 1 | Accepted ADR must change | Respected — none amended |
| 2 | V4 / Art XIV required | Respected — frozen file untouched |
| 3 | Dual execution authorities | Respected — ActionRegistry placed downstream |
| 4 | Proposed ADR treated as Accepted | Respected — 007/009/011 untouched |
| 5 | Historical evidence deleted | Respected — no deletions |
| 6 | Major WorkspaceOs/ActionRegistry redesign | Respected — one handler re-routed |
| 7 | Scope expansion (Brain/Goose/Predictive/OperatorKernel) | Respected |
| 8 | UI-thread / Art XVII budgets | Respected — launches move *off* the sync path |
| 9 | Tests assert bypass-without-receipt as desired | Not triggered — reconciled (see Tests) |
| 10 | O-1 re-interpreted as async expansion | Respected — no tier changes |
| 11 | `R1_UNGATED_STOP_LINE` hard stop | Respected |

**No ADR-006 / 012 / 013 / 014 component was re-wired.**

---

## Phase A acceptance

- [x] No successful capability or OS-action side effect completes without receipt + truth
- [x] The new gate is green (and demonstrably fails on a new bypass)
- [x] No dual authority introduced
- [x] No retired components resurrected

Phase B is **not** started, per the prompt's instruction to gate on Phase A.
