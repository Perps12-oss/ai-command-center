# Constitutional Pre-Flight — PR-UI-E07 Goal Workspace

**Slice:** PR-UI-E07 — Goal Workspace  
**Baseline:** `origin/main` @ `3529cbe` (post-E06 #96)  
**Builder:** Cursor (sole coder + Tom auditor)

---

## Authority checks

- [x] Constitution / UI Constitution Art. 16 (Goal Dashboard) + Art. 21
- [x] ADR-006 — no OperatorKernel; GOAL_SUBMIT_REQUEST remains submit-only
- [x] Evolve existing `GoalView` / `goal_dashboard` panels — do not delete Phase 11F surfaces
- [x] Roadmap E07

---

## Scope

1. Add `ui/components/goal/` — `goal_tree`, `task_row`, `success_criteria_card`, `goal_detail`
2. Evolve `GoalView` to compose tree + tasks + criteria + inspector select
3. Add `UI_GOAL_*` topics + controller publish helpers
4. Wire inspect for goal/task kinds
5. Tests under `tests/ui/views/test_goal_workspace_view.py`

No E08–E13 in this PR.

---

## AppState

- Fields added: **none** — project `brain_state` + `planner_last_plan`

---

## Pre-flight verdict

**GO**
