# Repository State Hygiene Disposition

**Date:** 2026-08-07  
**Baseline:** `origin/main` @ `16f549e`  
**Source:** Devin handover (worktree `C:/temp/aicc-e00`) → Cursor cloud closeout  
**Branch:** `cursor/repo-state-closeout-f30c`

---

## Executive disposition

| Item | Disposition | Rationale |
|------|-------------|-----------|
| `cursor/phase-b-canon-roadmap` (local, 1 commit ahead after rebase) | **ABANDON tip / salvage intent on tip truth** | Remote deleted; tip not in this clone or GitHub. Canon intent restored by refreshing the living roadmap against `main` @ `16f549e`. |
| `cursor/runtime-authority-audit` (local, 1 commit ahead after rebase) | **ABANDON tip / salvage intent on tip truth** | Same recoverability failure. Living Runtime Authority Map refreshed against tip + ADR-015–017 stop line. |
| `.agents/skills/adr-review/` (untracked in Devin worktree) | **N/A here** | Absent from this cloud clone (only `tom-auditor` skill present). No action. |
| `main-pre-sync-20260804` backup branch | **N/A here** | Absent from this clone. Safe to delete on any machine that still has it once tip rewrite is accepted. |
| Archived `[gone]` locals + tags | **Accepted as done** | Devin already archived/deleted; archive tags were local to that worktree and are not required on `origin`. |
| No-divergence rule | **SATISFIED in this clone** | Only local branch is `main` tracking `origin/main`; `git remote prune --dry-run` clean. |

---

## Recoverability note

The unique post-rebase commits for the two doc branches exist **only** on the
machine that held Devin's worktree (if still present). GitHub returns 404 for
both branch names. This closeout does **not** recreate those exact commits; it
re-applies the intended honesty corrections against current tip.

If the original 1-commit diffs are still needed for archaeology, recover them
from `C:/temp/aicc-e00` before deleting that worktree / `main-pre-sync-20260804`.

---

## Tip-truth salvage (this PR)

### Phase B roadmap

Verified on tip:

- PRs **#87–#103** (E00–E13) all **MERGED**
- Stage 1 CONDITIONS clearance **#105** **MERGED** (`TOM_AUDIT_PHASE_B_CONDITIONS_CLEARED.md`)
- Surfaces present: GlobalContextBar, OSPalette, NAV_GROUPS, Brain/Evidence/Operations/Graph/Insights views, extended InspectorHost kinds, UI_* topic families

Roadmap status updated from stale “ACTIVE remaining gaps” to **COMPLETE on main**
with residual non-blocking debt called out (not open E00–E13 work).

### Runtime Authority Map

Verified on tip via `service_factory.py`:

- Live path A (ExecutionAuthority → …) still canonical (ADR-006)
- GoalEngine / OperatorKernel / PlanningEngine / AgentCoordinator remain non-live
- SA.mutate stop line closed per `R1_UNGATED_STOP_LINE.md` (ADR-015/016/017)

Map baseline SHA and secondary Priority-3 section refreshed accordingly.

---

## Open PR hygiene (context only)

At closeout time, `origin` had one open product PR unrelated to this docs work:

- **#162** `cursor/exec-scrubber-phase3-drain-4c3f` — mergeable; CI in progress / mostly green

This disposition does not modify #162.

---

## Validation expected before merge

```bash
python3 -m pytest -m "not slow"
python3 -m ruff check ai_command_center
python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json
python3 scripts/verify_constitution.py
python3 tools/ucgs_runner.py > .ucgs_last.yaml
python3 tools/ucgs_ci_gate.py .ucgs_last.yaml
```
