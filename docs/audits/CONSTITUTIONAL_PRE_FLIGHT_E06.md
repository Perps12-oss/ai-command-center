# Constitutional Pre-Flight — PR-UI-E06 Brain Inspector

**Slice:** PR-UI-E06 — Brain Inspector  
**Baseline:** `origin/main` @ `759a492` (post-E05 #95)  
**Builder:** Cursor (sole coder + Tom auditor)

---

## Authority checks

- [x] Constitution / UI Constitution Art. 21
- [x] ADR-006 — no OperatorKernel as authority; project `BrainStateSnapshot` only
- [x] CURSOR_AUDIT_GATE — one slice; evolve, don’t rewrite Goal Dashboard
- [x] Roadmap E06

---

## Scope

New `BrainView` workspace projecting `AppState.brain_state`:

- Kernel state
- Goals (`goal_card`)
- Observations (`observation_card`)
- Runtime actions (`action_card`)
- Current plan (`plan_card`)

Wire: `view_manager`, `state_applier`, sidebar, `UI_BRAIN_*` / inspect select.

No E07 Goal Workspace rewrite in this PR.

---

## AppState

- Fields added: **none** — consume existing `brain_state`

---

## Pre-flight verdict

**GO**
