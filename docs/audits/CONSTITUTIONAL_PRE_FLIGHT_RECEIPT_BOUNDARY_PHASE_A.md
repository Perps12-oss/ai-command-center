# Constitutional Pre-Flight — Receipt Boundary (Phase A / G1–G3)

**Status:** PRE-FLIGHT (written before implementation, per `CLAUDE.md` → Art. X)
**Baseline SHA:** `59262fe08e04f5c5d0a5348eb6a3f0a702293cc4` (`origin/main`)
**Working branch:** `feat/receipt-boundary-phase-a`
**Scope:** Phase A only — A1 (close receipt boundary), A2 (close workspace-OS bypass), A3 (receipt-coverage gate).
**Source of task:** ACC Implementation Prompt (owner decisions O-1..O-4), audit `ACC_IMPLEMENTATION_STATE_AUDIT.md`.

---

## 1. Authority read (Art. II order)

| Level | Document | Bearing on this work |
|-------|----------|----------------------|
| 1 | `PROJECT_CONSTITUTION_V4.md` | Not amended. No Art. XIV / V4 change required. |
| 2 | `AGENTS.md`, `docs/ARCHITECTURE_ENFORCEMENT.md` | ADR-018 "sole `tool.invoke` publisher" preserved — see §4. |
| 3 | `docs/ARCHITECTURE.md`, contracts, topics | New capability names only; no new topics with authority semantics. |
| 4 | Accepted ADRs 006, 012–023 | None amended. ADR-018 strengthened, not changed. |
| 6 | Repository truth on `origin/main` | Re-verified against export; findings in §2. |

Proposed ADR-007 / 009 / 011 are **not** treated as binding (O-2 deferred to Phase C).

---

## 2. Verified defect statement (repository truth, not audit hearsay)

The audit called receipts "post-hoc observers." Direct code reading refines this into two
*specific, testable* defects, and corrects one audit claim.

### 2.1 Audit claim partially corrected — ordering is already sound

`EXECUTION_RUN_COMPLETE` / `EXECUTION_RUN_FAILED` appear in **neither** `SYNC_CRITICAL_TOPICS`
nor `ASYNC_ELIGIBLE_TOPICS` (`core/events/dispatch_policy.py:47,66`), so
`get_dispatch_tier` returns the `SYNC_STANDARD` default and `EventBus.publish`
takes the inline `_invoke_handlers` branch (`core/event_bus.py:381-392`).

Therefore `OrchestrationService._emit_completion` — receipt emission *and* truth validation —
**completes before `publish()` returns** to the orchestrator. The audit's G-5 bypass
("canonical runs succeeding before/without observer receipt") is **not** a race under
`async_dispatch=True`. This matters: it means the invariant can be enforced synchronously
at the completion contract without any new queue, barrier, or async tier work (respects O-1).

### 2.2 Real defect 1 — receipt is skipped entirely when `request_id` is empty

`services/orchestration_service.py` `_emit_completion`:

```python
request_id = str(payload.get("request_id") or payload.get("run_id") or "").strip()
if not request_id:
    return          # ← no receipt, no truth validation, run still reported successful
```

An `EXECUTION_RUN_REQUEST` carrying neither `request_id` nor `run_id` produces a real
side effect, publishes `EXECUTION_RUN_COMPLETE(success=True)`, and yields **no
`ExecutionReceipt` and no TruthBoundary validation**. This is a genuine G1 hole.

### 2.3 Real defect 2 — receipt emission is structurally optional

Nothing requires `OrchestrationService` to be subscribed. Removing it from composition
leaves `ExecutionOrchestratorService` publishing `EXECUTION_RUN_COMPLETE(success=True)`
with no receipt and no failure. Receipts are a *convention*, not a contract.

### 2.4 Real defect 3 (G2) — workspace OS launches never reach the boundary

`core/workspace_os_service.py:254 _on_launch_resource` publishes `ACTION_INVOKE_REQUEST`
→ `ActionRegistry.invoke` → frozen handlers in `core/workspace_os_actions.py`
(`webbrowser.open`, `os.startfile`, `subprocess.run`). No `tool.invoke`, no
ExecutionAuthority, no receipt, no truth. `workspace_os_enabled` defaults to `True`
(`application.py:55`).

---

## 3. Chosen loci (and the ones rejected)

The prompt allows three loci for A1: execution-completion contract, capability/executor
contract, or response gating. **Chosen: execution-completion contract**, because it is the
narrowest point that dominates every capability path and it is already single-authority.

| Option | Verdict |
|--------|---------|
| Response gating (`CHAT_COMPLETE`) | Rejected — gates the *message*, not the *run*; a run with no `request_id` never reaches it. |
| Capability/executor contract (per-tool) | Rejected — would need enforcement duplicated in ToolExecutor, ChatHandler and every future executor; violates Inv 11. |
| **Execution-completion contract** | **Chosen** — one locus, already the sole `EXECUTION_RUN_COMPLETE` publisher, and inline dispatch (§2.1) makes it verifiable synchronously. |

---

## 4. Authority analysis — why this does not create a second authority

**A1.** `ExecutionOrchestratorService` remains the sole decider of run outcome. It gains a
*self-check*: "did the evidence this run is contractually required to produce actually
appear?" A component verifying its own contract is not a second authority — it is the
existing authority refusing to report unverified success. No new service is introduced;
no component gains the ability to *start* work.

**A2.** `ActionRegistry` is placed **downstream** of `TOOL_INVOKE`, in the same position
`ToolExecutorService` already occupies. It gains **no** ability to initiate execution — it
only executes what the sole `TOOL_INVOKE` publisher dispatched. ADR-018's "sole
`tool.invoke` publisher" is preserved exactly: `ExecutionOrchestratorService` remains the
only publisher. This is the explicit "do not give ActionRegistry parallel execution
authority" constraint, satisfied by moving it *below* the boundary rather than beside it.

**Frozen-file question resolved.** `core/workspace_os_actions.py` is annotated
"FROZEN … DO NOT MODIFY without constitutional amendment." The chosen design leaves that
file **byte-identical**. Its handlers are reused (not duplicated — Inv 11) by importing
them; the re-route happens in `workspace_os_service.py`, which carries no freeze marker.
No constitutional amendment is therefore required, and stop conditions 2 and 6 are not
triggered.

---

## 5. Known behavioural change (declared, not hidden)

`_on_launch_resource` today calls `_await_result`, which is **not** blocking — it pops a
dict populated by synchronous dispatch (`workspace_os_service.py:227-229`). Routing
launches through `TOOL_INVOKE` (an `ASYNC_ELIGIBLE` topic, enqueued when
`async_dispatch=True`) means the result is no longer available synchronously.

Consequence: **launch failures stop raising `ValueError` synchronously from the UI handler**
and instead surface through the receipt / truth / `CHAT_COMPLETE` path.

This is a deliberate consequence of bringing the path inside the boundary, and is the
behaviour the prompt asks for ("obtain receipts, or fail closed"). It is *not* a
WorkspaceOs redesign: the request/await machinery, ActionRegistry, and the frozen handlers
are all structurally unchanged. Flagged here for owner visibility.

---

## 6. Stop conditions — pre-flight assessment

| # | Condition | Status |
|---|-----------|--------|
| 1 | Accepted ADR must change | NOT TRIGGERED — ADR-018 strengthened, text unchanged |
| 2 | V4 / Art XIV required | NOT TRIGGERED — frozen file untouched (§4) |
| 3 | Dual execution authorities | NOT TRIGGERED — ActionRegistry placed downstream (§4) |
| 4 | Proposed ADR treated as Accepted | NOT TRIGGERED — 007/009/011 untouched in Phase A |
| 5 | Historical evidence deleted | NOT TRIGGERED — no deletions |
| 6 | Major WorkspaceOs/ActionRegistry redesign | NOT TRIGGERED — one handler re-routed (§5) |
| 7 | Scope expands to Brain/Goose/Predictive/OperatorKernel | NOT TRIGGERED |
| 8 | UI-thread / Art XVII budget violated | NOT TRIGGERED — no new sync work on UI thread; launches move *off* the sync path |
| 9 | Tests assert bypass-without-receipt as desired | TO BE CONFIRMED during implementation |
| 10 | O-1 re-interpreted as async expansion approval | NOT TRIGGERED — no tier changes; design deliberately avoids needing them (§2.1) |
| 11 | `R1_UNGATED_STOP_LINE` hard stop crossed | NOT TRIGGERED |

---

## 7. Verification plan

1. Failing-first tests for §2.2, §2.3, §2.4 (each must fail at `59262fe`).
2. Receipt-coverage gate (A3): **enumerative** — scans `ai_command_center/` for
   `subprocess`/`Popen`/`os.startfile`/`webbrowser.open` call sites and asserts each is
   either inside the execution boundary or on an explicit, severity-annotated allowlist
   carrying the audit's out-of-scope bypasses (chat export, MCP inspector, QwenPaw
   sidecar). A *new* bypass fails the build.
3. `verify_constitution.py`, `arch_lint.py`, `ruff`, `pytest -m "not slow"`.

---

## 8. Deliberately left alone

- Async EventBus tiers (O-1 waiver — no tier list changes).
- `provider_sdk/` and unused adapters (O-3 dormant).
- `operator/`, `orchestration/execution|routing|policies` paper stack (unwired).
- External / `mcp.*` weak handlers (G7, Goose Stage 3 gated).
- Chat export, MCP inspector, QwenPaw sidecar side effects — allowlisted with severity,
  not fixed (out of Phase A scope per the audit's own register).
