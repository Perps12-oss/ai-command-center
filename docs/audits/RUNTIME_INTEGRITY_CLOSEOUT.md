# Runtime Integrity Closeout Ledger

**Date:** 2026-08-12  
**Baseline:** `cursor/runtime-integrity-closeout-4b28` (includes PR #175 control-plane remediation)  
**Role:** Canonical post-audit closeout — **not** an implementation queue  
**Canonical plan:** `docs/governance/IMPLEMENTATION_GUIDE.md` (Strategic Runtime Program; this ledger is not Queue 1)

---

## Closeout verdict

**COMPLETE WITH PARKED ITEMS** — §4 "NO bypass found" overturned by `docs/audits/TOOL_TIER_SECURITY_CLOSEOUT.md` (SecurityTier at `TOOL_INVOKE`; PR #177 superseded).

Remediation of known audit findings is closed. Parked items are explicitly classified below and are **not** Queue 1 work.

---

## EventBus shutdown disposition

**Code change required:** YES (minimal).

**Defect:** `_dispatch_worker` exited on `_shutdown.is_set()` before draining accepted queue jobs; post-shutdown async publishes fell back to synchronous delivery.

**Fix:** `ai_command_center/core/event_bus.py`
- Worker drains until `None` sentinel (FIFO preserved)
- Post-shutdown `ASYNC_ELIGIBLE` publishes return `delivery="dropped"`
- `SYNC_CRITICAL` inline behavior unchanged

**Proof:** `tests/test_eventbus_shutdown.py` (6 tests) + existing `test_eventbus_dispatch_queue.py`, `test_eventbus_async_adapters.py`

---

## Live authority disposition (duplicate review)

| Suspected duplicate | Classification | Authoritative owner | Action |
|---------------------|----------------|---------------------|--------|
| `active_workspace_id` (EA, StateAuthority, WorkspaceService, AppState snapshot) | **B — derived/snapshot** | `WorkspaceService` + `WORKSPACE_ACTIVE` bus facts; AppState projects read model | **No change** |
| Domain snapshots vs runtime dataclasses | **B — projection** | Services/repos own mutation; snapshots are UI/AppState projections | **No change** |
| Retired packages (`operator/`, `goal_engine/`, etc.) | **C — retired** | Not in `service_factory.py` / `application.py` | **Preserve** (historical evidence) |
| `BrainRuntimeService` vs `ExecutionOrchestratorService` approval | **D — different paths** | Orchestrator = ADR-018 plan steps; Brain runtime = `RUNTIME_ACTION_REQUEST` tier path | **No merge** |
| `PermissionService` vs orchestrator HITL | **D — parallel boundaries** | HITL = intention confirmation; Permission = `LAUNCH_TOOL` for non-interactive shell | **No merge** (by design post-#175) |

**No true live duplicate authorities required code deletion in this closeout.**

---

## Security regression result (post-#175)

`tests/test_control_plane_security_acceptance.py` — **19 passed** (2026-08-12 closeout run).

Attack model outcomes on ADR-018 primary path:

| Attack | Expected | Result |
|--------|----------|--------|
| `actor_type=user` from LLM payload | Rejected / remains agent | **PASS** |
| `auto_approve=true` suppresses mandatory approval | Cannot suppress | **PASS** |
| `require_approval=true` | Pauses until approval | **PASS** |
| Missing / invalid approval | Fail closed | **PASS** |
| Agent `workspace_execute_command` | Permission boundary | **PASS** |
| `python -c ...` | Blocked | **PASS** |
| Interactive UI shell + approval | Executes with receipt | **PASS** |
| Workflow shell | LAUNCH_TOOL + no per-step HITL | **PASS** |

**Falsification question:** Can an LLM-generated action execute privileged/arbitrary work without explicit authorization? **NO** on primary ADR-018 path.

---

## Finding ledger

| Finding | Evidence | Disposition | Proof |
|---------|----------|-------------|-------|
| UCGS staged-vs-range defect | PR #170 `.github/workflows/ucgs.yml` | **FIXED** | `UCGS_DIFF_MODE=range`, `fetch-depth: 0` on main |
| SQLite lock discipline | PR #170 `GuardedConnection` | **FIXED** | `tests/test_p1_*`, data-access modules |
| EA unconditional `auto_approve=True` | `execution_authority_service.py` pre-#175 | **FIXED** | PR #175; acceptance tests |
| `auto_approve` suppresses `require_approval` | `execution_orchestrator_service.py` pre-#175 | **FIXED** | `core/control_plane.py`; acceptance tests |
| Actor identity payload spoofing | orchestrator + tool executor pre-#175 | **FIXED** | PR #175 `resolve_run_context` / `interactive_user` |
| Shell permission boundary (`workspace_execute_command`) | PR #170 + #175 actor fix | **FIXED** | `test_p1_execution_permission_boundary.py`, acceptance tests |
| `python -c` sandbox escape | `command_sandbox.py` allowlist | **FIXED** | PR #175 blocks `-c`/`--command`; acceptance test |
| Workspace command authority | EA → orchestrator sole `TOOL_INVOKE` publisher | **FIXED** | `test_execution_authority_hardening.py` AST gate |
| EventBus async architecture (R4b single queue) | `application.py`, `event_bus.py` | **FIXED** (live) | dispatch/adapter tests |
| EventBus shutdown/drain | `event_bus.py` worker loop pre-closeout | **FIXED** | `tests/test_eventbus_shutdown.py` |
| Receipts / TruthBoundary | `OrchestrationService`, receipt emit | **FIXED** (live) | `test_receipt_boundary.py` |
| HITL infrastructure | `tool.confirmation_*`, ApprovalsView | **FIXED** (live post-#175) | `test_tool_confirmation_adr009.py`, acceptance tests |
| `active_workspace_id` duplication | EA cache vs WorkspaceService vs AppState | **ACCEPTED RISK** (derived projections) | Authority table above |
| Retired/importable packages | `operator/`, `goal_engine/`, etc. | **RETIRED / ABANDONED** | Not in factory; truth matrix |
| God-object / AppState size | Observation | **PARKED** | Not a defect; no Queue 1 ticket |
| UI coverage gaps | Observation | **PARKED** | Not remediation scope |
| Domain/snapshot duplication | Multiple snapshot types | **ACCEPTED RISK** (projection layers) | No live dual-writer |
| ADR-009 formal status Proposed | `adr/README.md` | **PARKED** | Live-in-effect; formal acceptance is docs-only |
| ADR-021 parked extras | ADR text | **PARKED** | Not Queue 1 |
| ADR-022 parked threshold | ADR text | **PARKED** | Not Queue 1 |
| ADR-008 compaction | ADR text | **PARKED** | Not Queue 1 |
| Phase 5 tiered EventBus pools | `IMPLEMENTATION_GUIDE` Queue 1 | **PARKED** | Branch abandoned; single queue canonical |
| OperatorKernel | ADR-006 | **RETIRED / ABANDONED** | Truth matrix |
| GoalEngine | ADR-012 | **RETIRED / ABANDONED** | `SingleGoalScheduler` live |
| PlanningEngine | ADR-013 | **RETIRED / ABANDONED** | `PlannerService` live |
| AgentCoordinator | ADR-013 | **RETIRED / ABANDONED** | `AgentRuntimeService` live |
| PredictiveEngine | ADR-014 | **RETIRED / ABANDONED** | Research only |
| UndoReplay | ADR-014 | **RETIRED / ABANDONED** | Timeline/Snapshot live |
| Knowledge Federation programme | Historical plans | **RETIRED / ABANDONED** | Fossil index |
| Goose / provider SDK live-wire | Queue 2 evaluate | **PARKED** | Integration proposal required |
| macOS/Linux platform hotkey/tray | Phase 11 backlog | **PARKED** | Truth matrix GATED rows |
| Control-plane audit doc stale narrative | `CONTROL_PLANE_SECURITY_AUDIT.md` | **FIXED** | Historical banner added |

---

## Verification (2026-08-12)

| Gate | Result |
|------|--------|
| `tests/test_eventbus_shutdown.py` | 6 passed |
| `tests/test_control_plane_security_acceptance.py` | 19 passed |
| `pytest -m "not slow"` | 1429 passed, 5 skipped |
| `ruff check ai_command_center` | pass |
| `scripts/verify_constitution.py` | pass |
| `scripts/arch_lint.py` | pass (baselined) |
| `tools/ucgs_ci_gate.py` | pass (S2 warnings) |

---

## Remaining parked / accepted items

- Phase 5 tiered EventBus pools (requires measured contention + owner gate)
- Platform hotkey/tray live wire (Phase 11)
- Goose/provider SDK patterns (Queue 2 — proposal only)
- ADR formalization backlog (009, 021, 022, 008 status fields)
- AppState decomposition / UI coverage (observations only)
- `git` on sandbox allowlist (permission + HITL bound; not arbitrary execution primitive alone)

---

## Canonical repository state

| Field | Value |
|-------|-------|
| **Current implementation authority** | `origin/main` live code + `PROJECT_CONSTITUTION_V4.md` + Accepted ADRs |
| **Current Queue 1** | **EMPTY** |
| **Historical authority** | `HISTORICAL_AND_RETIRED_WORK.md`, fossil audits, Proposed ADRs |
| **Runtime authority** | `ExecutionAuthorityService` intake → `SingleGoalScheduler` → `ExecutionOrchestratorService` → sole `TOOL_INVOKE` publisher |
| **Security authority** | `core/control_plane.py` + orchestrator HITL + `PermissionService` + `CommandSandbox` |
| **Remaining open implementation work** | **None approved** — owner must choose next product/architecture priority |

---

## Final recommendation

**YES** — the remediation programme for known audit findings is closed. The next work should be **new product/architectural work chosen by the owner**, not further remediation of items in this ledger.

Do not reopen control-plane design unless a new bypass is demonstrated with failing falsification tests.
