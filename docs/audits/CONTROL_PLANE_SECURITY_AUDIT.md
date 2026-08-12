# Control-Plane Security Audit (Focused)

**Date:** 2026-08-12  
**Baseline:** `origin/main` @ `1ee05ba`  
**Status:** FINDINGS — acceptance tests in `tests/test_control_plane_security_acceptance.py` encode required invariants (fail on `main` until fix)  
**Scope:** Approval authority, actor identity, shell/tool authority only — not a repo-wide fossil pass.

---

## A. Approval authority — one answer

### Question

What exact component is **authoritative** for deciding whether execution requires human approval?

### Answer (required invariant)

**`ExecutionOrchestratorService._step_needs_approval()`** is the sole gate that can pause a plan step and emit `tool.confirmation_required` / `EXECUTION_STEP_AWAITING_APPROVAL` on the ADR-018 path (planner → orchestrator → `TOOL_INVOKE`).

No other component may override that gate for the same run.

### What each listed component actually does

| Component | Role today | Authoritative for HITL on plan steps? |
|-----------|------------|--------------------------------------|
| **ExecutionAuthorityService** | Intake; builds synthetic plans with `require_approval=False` (`_plan_for_decision`, line 773) and sets **`auto_approve: True`** on every `GOAL_SUBMIT_REQUEST` (line 544) | **No** — actively **suppresses** orchestrator approval |
| **SingleGoalScheduler** | Forwards `auto_approve` from payload into `EXECUTION_RUN_REQUEST` (`goal_scheduler_service.py:398`) | **No** — transport only |
| **ExecutionOrchestratorService** | `_step_needs_approval(step, auto_approve)`; emits `tool.confirmation_required` when true | **Yes** (when not bypassed) |
| **PlanStep.require_approval** | Input to `_step_needs_approval` | **Conditional** — ignored when `auto_approve` is true |
| **`tool.confirmation_required`** | Event surface (ADR-009); not a decision engine | **No** — notification |
| **`tool.approved` / `tool.denied`** | Resume/deny after human decision | **No** — consumer of UI decision |
| **ApprovalsView** | Renders `pending_tool_confirmations` + permission snapshot | **No** — UI only |
| **PermissionService** | `LAUNCH_TOOL` etc. for **tool.invoke** path (`tool_executor_service._shell_allowed`) | **Parallel boundary** for shell tools — not wired to orchestrator HITL |
| **SecurityTier** | Used by **BrainRuntimeService** `RUNTIME_ACTION_REQUEST` path (`WRITE_DESTROY` + `require_approval`) | **Separate path** — not EA → scheduler → orchestrator |
| **TruthBoundary** | Post-execution receipt/narrative grounding | **No** — not an approval authority |

### Bypass (live defect)

```text
EA._submit_plan → auto_approve=True (always)
       ↓
Scheduler → EXECUTION_RUN_REQUEST.auto_approve=True
       ↓
Orchestrator._step_needs_approval → False (short-circuit)
       ↓
tool.confirmation_required NEVER emitted
```

Synthetic EA plans also hardcode `require_approval=False` for shell and all skip-planner capabilities.

**There is not one authoritative approval story today** — two paths exist (Brain runtime vs orchestrator), and the **primary product path bypasses orchestrator HITL entirely**.

---

## B. Actor identity

### Where `actor_type` originates

| Origin | Sets `actor_type`? | Trusted? |
|--------|-------------------|----------|
| **ExecutionOrchestrator** `_dispatch_step` | `step.args.get("actor_type") or "user"` | **Must not trust payload** |
| **EA workflow intake** | `"workflow"` in step args | Stamped by EA (good) |
| **EA synthetic plans** | Not set → orchestrator defaults **`user`** | **Spoofable via plan args** |
| **TOOL_INVOKE direct publish** | `payload.get("actor_type", "user")` | **Caller supplies** |
| **PermissionService** | `payload.get("actor_type", "agent")` on bus handler | Payload-controlled |

### Can the caller / LLM / serialized goal supply it?

| Vector | Answer |
|--------|--------|
| Caller publishes `TOOL_INVOKE` | **Yes** — defaults to `"user"` |
| LLM / planner puts `actor_type` in `step.args` | **Yes** — orchestrator copies to `TOOL_INVOKE` |
| UI input | UI commands go through EA; orchestrator still defaults missing to **`user`** |
| Serialized goal / plan JSON | **Yes** — `PlanStep` deserializes `args` verbatim |
| Scheduler/orchestrator should trust it? | **No** — must stamp from intake authority + run provenance |

### `_shell_allowed` compounding

`actor_type == "user"` → **returns True unconditionally** (no `PermissionService` check).  
Combined with orchestrator default `"user"`, agent/LLM paths can inherit **full user shell privilege**.

---

## C. Shell / tool authority

### Entry points audited

| Path | Gate before subprocess |
|------|------------------------|
| `workspace_execute_command` → `_execute_command` | `CommandSandbox.validate_command` + `_shell_allowed` (since #170) |
| `shell` tool (`tool_executor_service`) | `_shell_allowed` + sandbox in handler |
| `CommandSandbox` | Allowlist includes **`python`**, **`git`** — first token only |
| `subprocess.run` | `workspace_os_actions._execute_command` — `shell=False` |

### Critical question

**Can an unapproved LLM-generated action reach arbitrary code execution?**

**Yes, on current `main`, via compounding defects:**

1. **No orchestrator HITL** (`auto_approve=True`).
2. **`actor_type` defaults to `user`** → `_shell_allowed` passes without `LAUNCH_TOOL`.
3. **`python` is allowlisted** → `python -c '__import__("os").system(...)'` passes `CommandSandbox` (argv[0] is `python`).

`git` in allowlist is a similar primitive (e.g. config/exec hooks depending on invocation).

### What is NOT the fix alone

Shrinking the allowlist helps but does not replace **approval authority** and **non-spoofable actor identity**.

---

## Acceptance tests (before fix)

See `tests/test_control_plane_security_acceptance.py` — marked `control_plane_acceptance`.  
**Expected on `main` (2026-08-12):** **8 xfailed, 11 passed** — xfailed tests encode live defects (`strict=True`; remove xfail in remediation PR).

### Adversarial audit question (post-fix)

> Can an LLM-generated action execute privileged or arbitrary work without an explicit authorization decision?

Run after fix:

```bash
APPDATA=/tmp/aicc_appdata python3 -m pytest tests/test_control_plane_security_acceptance.py -m control_plane_acceptance
```

---

## Remediation direction (not implemented here)

1. Remove unconditional `auto_approve: True` from EA; derive from `SecurityTier` / `require_approval` / capability risk.
2. Stamp `actor_type` (and `actor_id`) at orchestrator from run provenance — **reject** payload escalation.
3. Treat `user` as interactive-only (UI session), never from plan args or `TOOL_INVOKE` payload.
4. High-risk tools (`shell`, `workspace_execute_command`, `python`, `git`) require orchestrator HITL **and** permission check for non-interactive actors.
5. Narrow sandbox: remove `python`/`git` from default allowlist or require structured subcommands.
