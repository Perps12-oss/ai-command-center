# Handover — Phase A + Phase B → Cursor

**Branch:** `feat/receipt-boundary-phase-a`
**Base:** `origin/main` @ `59262fe` (post-PR #165)
**Commits:** `3709325` (Phase A) · `8a4a7a0` (governance correction) · `0e56b37` (Phase B)
**Implementation role:** Claude Code (never an authority — `CLAUDE.md`)

---

## 1. State of play

| Phase | Status |
|-------|--------|
| **A** — receipt boundary (G1/G2/G3) | **COMPLETE**, gate green |
| **Governance correction** — stale UCGS contract lock | **COMPLETE** |
| **B** — intake authority convergence (B1–B4) | **COMPLETE** |
| **B5** — direct `GOAL_SUBMIT_REQUEST` intake | **CLOSED (fork 1)** — see `B5_HERO_EA_INTAKE_CHANGE_NOTE.md` |
| **C** — docs↔code reconciliation | **NOT STARTED** — backlog seeded |

**Not on `main` yet.** `PHASE_COMPLETION_RULE.md`: a phase is complete only on `main`.
Nothing here may be declared phase-complete until this branch merges.

---

## 2. What each commit did

### `3709325` — Phase A: receipt boundary

Production side effects can no longer complete *successfully* without an `ExecutionReceipt`
and TruthBoundary validation.

- `OrchestrationService._emit_completion` no longer early-returns when `request_id`/`run_id`
  are absent (it synthesizes an id) — that hole produced **no receipt at all**.
- `ExecutionOrchestratorService` records `ORCHESTRATION_RECEIPT` ids and verifies one exists
  after completing a run; if not it publishes `EXECUTION_RUN_FAILED` with
  `receipt_boundary_violation: True`.
- `UI_LAUNCH_RESOURCE` now enters ExecutionAuthority via `WORKFLOW_EXECUTION_REQUEST` instead
  of going straight to `ActionRegistry`. New `orchestration/workspace_launch_tools.py`
  **imports** the frozen handlers — `core/workspace_os_actions.py` is **byte-identical**.
- `tests/test_receipt_coverage_gate.py` — enumerative AST scan of every
  `subprocess.*` / `os.startfile` / `webbrowser.open` site. **Verified it fails on an
  injected bypass.**

**Audit correction made here:** `EXECUTION_RUN_COMPLETE` is in neither dispatch tier set, so
it defaults to `SYNC_STANDARD` and dispatches **inline**. The reported ordering race does not
exist, which let the boundary be enforced synchronously with no EventBus tier changes (O-1).

### `8a4a7a0` — governance correction

`ucgs.profiles/ai-command-center.yaml` required `COMMAND_ROUTED_VERSION`, retired in
`8002c72` (#80, 2026-07-20). Dormant until Phase B touched `contracts.py`, then
`S4/block_merge`. One line removed. Enforcement proven intact by probe.

### `0e56b37` — Phase B: intake convergence

- All three EA intakes now call shared `_publish_decision()` + `_admit()`.
- `_workspace_optional()` — gate keyed on **capability**, not intake.
- Decisions carry `intake` provenance; `chat_state` ignores non-`ui_command`.
- Workflows with no executable tool step now fail explicitly instead of stalling.

---

## 3. ⚠️ Things Cursor must not undo

| Do not | Why |
|--------|-----|
| Re-add `COMMAND_ROUTED_VERSION` | Retired contract. Would re-block all `contracts.py` edits. |
| Modify `core/workspace_os_actions.py` | FROZEN. Phase A deliberately kept it byte-identical to avoid a constitutional amendment. |
| Duplicate `is_executable_workflow_step` | Single owner in `core/contracts.py` (Inv 11). Two copies silently reintroduce the stuck-run defect. |
| Restore the `INTENT_AGENT` deferral branch | Removed under a recorded Article VI supersession. |
| Relax `_receipted_ids` clearing in `ExecutionOrchestratorService` | Both clears are defense-in-depth; removing **both** reintroduces the stale-receipt defect. |
| Add side effects outside the boundary | `tests/test_receipt_coverage_gate.py` will fail the build. Route through `TOOL_INVOKE` or add a severity-annotated allowlist entry deliberately. |
| Expand EventBus async tiers | O-1 waiver. Blocked. |
| Wire `provider_sdk` adapters | O-3 dormant. |
| Re-wire OperatorKernel / GoalEngine / PlanningEngine / AgentCoordinator | ADR-006/012/013 retired; needs a superseding ADR. |

---

## 4. Deliberate behaviour changes (do not treat as bugs)

1. **`agent: <task>` with no active workspace no longer defers.** Recorded gate supersession
   — `docs/audits/GATE_SUPERSESSION_WORKSPACE_REQUIRED_AGENT.md`.
2. **Workspace-OS launch failures no longer raise `ValueError` synchronously.**
   `_await_result` was never blocking; `TOOL_INVOKE` is `ASYNC_ELIGIBLE`. Errors now surface
   via receipt / truth / `CHAT_COMPLETE`. No UI caller caught that exception.
3. **Workflow/agent runs now emit `EXECUTION_AUTHORITY_DECISION`.** Authority telemetry and
   system-monitor counts rise. `telemetry_summary.py:130` counts by
   `bus_source == "execution_authority"` — dashboards keyed on that shift.

---

## 5. Open items

### B5 — Authority Boundary: direct `GOAL_SUBMIT_REQUEST` intake (owner decision needed)

`ui/controller.py:839 publish_goal_submit_request()` publishes straight to
`SingleGoalScheduler`, bypassing ExecutionAuthority. Callers: `ui/shell/view_manager.py:616`,
`ui/views/goal_view.py` (Hero "New Goal").

Already receipted → **not** a receipt-boundary defect. It **is** an authority-provenance
question, and a possible Inv-1 shortcut. Open question, deliberately not assumed:

1. Is `GOAL_SUBMIT_REQUEST` an internal post-authority command that must never be published
   externally? or
2. A legitimate intake needing its own authority decision?

### Phase C

- `docs/audits/PHASE_C_BACKLOG_GOVERNANCE_FOSSILS.md` — F-1 stale `pipeline.canonical`,
  F-2 misleading `eventbus_bypass.remediation`. **Systematic pass, not opportunistic fixes.**
- Original Phase C scope still outstanding: Phase 7 roadmap honesty (C1), Phase 5 async
  waiver (C2), Phase 8/10 hygiene (C3), ADR-007/009/011 (C4).
- **G5/B2 confirmed still open:** `_publish_decision_and_autonomy` has only 2 call sites
  (`:379` awaiting-approval, `:705` replan-stuck) — no DecisionRecord/AutonomyScore on normal
  success or ordinary failure.
- **G6:** only **7** test files reference `create_application` (audit claimed ~15).

---

## 6. Verification on this host

```bash
python scripts/verify_constitution.py            # PASS
python scripts/arch_lint.py --baseline tests/arch_lint_baseline.json   # OK (4 baselined)
python scripts/verify_contracts.py               # PASS
python -m ruff check ai_command_center           # clean
APPDATA=/tmp/aicc_appdata python -m pytest -m "not slow"   # 1384 passed, 2 failed
```

**The 2 failures are pre-existing at `59262fe`** — `test_chat_message_height_c7`,
`test_program3_exit_gate`. Confirmed during Phase A by re-running with source stashed.
tkinter/Tcl unavailable on this host. **Do not attribute them to this work.**

`ruff check tests/` reports ~66 pre-existing issues repo-wide; the documented gate is
`ruff check ai_command_center`. All files added here are clean.

---

## 7. Method notes

Every new behaviour was **proven failing before the change** — by stash-and-run, or by
mutation (reintroducing the defect and confirming the test fails). Two cases where the naive
check would have misled:

- The receipt-coverage gate had to be **AST-based**: a regex matched `subprocess.run` inside
  a *docstring*.
- The stale-receipt test only fails when **both** clears are removed. Stated explicitly in
  the change note rather than implying tighter coverage than exists.

Pre-existing failures were isolated by `git stash` before being attributed.

---

## 8. Local environment note (not part of any commit)

`scratchpad/CLAUDE.md.local-backup` (1576 bytes) is a **local** `CLAUDE.md` that differed
from the tracked baseline. Preserved at owner instruction for the next governance/runtime
review. **Not merged, not deleted, not committed.** Path:
`AppData/Local/Temp/claude/C--Users-S8633/<session>/scratchpad/CLAUDE.md.local-backup`.

Also uncommitted and untouched: `.claude/`, `.agents/skills/adr-review/`.
