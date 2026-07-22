# E07 — Goal Workspace

**Slice:** PR-UI-E07  
**Status:** Implemented on feature branch (pending merge)

## Purpose

Evolve `GoalView` into a Goal Workspace with tree, tasks, success criteria, and inspector selection — without deleting Phase 11F Goal Dashboard panels.

## Composition

```
GoalView
├── Hero (metrics, New Goal → GOAL_SUBMIT_REQUEST)
├── Workspace row
│   ├── GoalTree
│   ├── Tasks (TaskRow list from plan steps)
│   └── GoalDetail → SuccessCriteriaCard
└── Phase 11F panels (GoalList / Detail / Progress / Plan / History)
```

## State

- Reads `AppState.brain_state` + `planner_last_plan` via `resolve_plan`
- No new AppState fields

## Topics

| Topic | Intent |
|-------|--------|
| `ui.goal.select` | Goal focused |
| `ui.goal.task_select` | Plan step focused |
| `ui.goal.open` | Open goals workspace |

Selection also publishes `UI_INSPECT_SELECT` for goal / plan_step kinds.
