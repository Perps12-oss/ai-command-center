# Goal Engine

**Status:** Proposed Phase 0 contract, pending approval  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `docs/architecture/VNEXT_STATE_DRIVEN_BLUEPRINT.md`

## Purpose

The Goal Engine defines how user intent becomes schedulable work. It owns contracts, validation, and success criteria semantics. It does not plan actions, execute tools, or mutate the World Model.

## Domain model

```text
Goal
  id: string
  title: string
  description: string
  priority: Priority
  depends_on: list[string]
  tasks: list[Task]
  success_criteria: list[SuccessCriteria]
  status: draft | queued | active | paused | complete | failed | cancelled
  correlation: CorrelationContext

Task
  id: string
  goal_id: string
  title: string
  description: string
  depends_on: list[string]
  status: pending | ready | active | blocked | complete | failed | cancelled
  success_criteria: list[SuccessCriteria]
  correlation: CorrelationContext

SuccessCriteria
  id: string
  description: string
  verifier: manual | event | world_model_query
  expected: object
```

## Priority v1

```text
Priority = CRITICAL | HIGH | NORMAL | LOW
```

Priority controls scheduler ordering before activation. It must not bypass approval gates, runtime safety, dependency checks, or repository ownership.

## Dependencies v1

`depends_on` is a simple list of goal or task IDs.

Rules:

- If a dependency is unresolved, the dependent goal or task is blocked.
- If a dependency fails, the dependent goal or task fails unless the user revises it.
- Dependencies are explicit only. The planner may suggest dependencies, but the Goal Engine validates them.

## Correlation context

Every goal and task includes:

```text
CorrelationContext
  correlation_id: string
  goal_id: string?
  action_id: string?
```

The `correlation_id` is created when the user goal enters the system. It propagates to events, logs, journal entries, action results, approvals, and errors.

## Interfaces

```text
IGoalRepository
  save_goal(goal: Goal) -> void
  get_goal(id: string) -> Goal?
  list_goals(status: string?) -> list[Goal]
  update_goal_status(id: string, status: string, correlation: CorrelationContext) -> void

IGoalValidator
  validate_goal(goal: Goal) -> ValidationResult
  validate_dependencies(goal: Goal) -> ValidationResult
  validate_success_criteria(goal: Goal) -> ValidationResult
```

## Implementation v1

Use repository-backed persistence for goals and tasks. Keep execution single-process and single-active-goal through `SingleGoalScheduler`.

Success criteria v1 supports:

- Manual confirmation.
- Event observed on EventBus.
- World Model query through repository-backed services.

## Forbidden behavior

- Goal Engine must not execute actions.
- Goal Engine must not call tools.
- Goal Engine must not call planners directly.
- Goal Engine must not read or write SQLite outside repositories.
- Goal Engine must not create hidden global state.

## Verification

- A goal with an unresolved dependency is blocked.
- A goal with invalid priority is rejected.
- A task completion records correlation through logs, events, and journal.
- A failed dependency prevents dependent task execution.
