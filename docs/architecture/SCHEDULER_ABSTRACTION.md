# Scheduler Abstraction

**Status:** Proposed Phase 0 contract, pending approval  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `docs/ARCHITECTURE.md`

## Purpose

The scheduler accepts user goals and exposes the next executable task to the kernel. It does not plan, execute, persist world state, or call tools.

The v1 scheduler is intentionally single-active-goal. It preserves an interface that can support richer scheduling later without rewriting the kernel.

## Core contracts

```text
Goal
  id: string
  title: string
  description: string
  priority: CRITICAL | HIGH | NORMAL | LOW
  depends_on: list[string]
  success_criteria: list[SuccessCriteria]
  correlation: CorrelationContext

Task
  id: string
  goal_id: string
  title: string
  description: string
  status: pending | ready | active | blocked | complete | failed | cancelled
  depends_on: list[string]
  success_criteria: list[SuccessCriteria]
  correlation: CorrelationContext
```

## IScheduler

```text
IScheduler
  submit_goal(goal: Goal) -> void
  pause_goal(goal_id: string, correlation: CorrelationContext) -> void
  resume_goal(goal_id: string, correlation: CorrelationContext) -> void
  cancel_goal(goal_id: string, correlation: CorrelationContext) -> void
  get_next_task(correlation: CorrelationContext) -> Task?
  complete_task(task_id: string, result: ActionResult) -> void
  fail_task(task_id: string, error: RuntimeErrorRecord) -> void
  list_goals() -> list[Goal]
```

## Implementation v1: SingleGoalScheduler

`SingleGoalScheduler` maintains:

- One active goal.
- A FIFO queue of pending goals.
- Sequential execution of tasks inside the active goal.
- No worker pool.
- No parallel task execution.

If multiple goals are queued, they run sequentially. `CRITICAL`, `HIGH`, `NORMAL`, and `LOW` affect queue ordering only before a goal becomes active. Once active, a goal is not preempted unless the user pauses or cancels it.

## EventBus behavior

Scheduler events must include `CorrelationContext`.

```text
goal.submitted
goal.activated
goal.paused
goal.resumed
goal.cancelled
task.ready
task.completed
task.failed
```

These topics are proposed names for Phase 1 contract registration. They must be added to `ai_command_center/core/events/topics.py` only during implementation after this document is approved.

## Forbidden behavior

- Scheduler must not import planners.
- Scheduler must not import runtime executors.
- Scheduler must not call tools.
- Scheduler must not mutate the World Model directly.
- Scheduler must not maintain authoritative world state.

## Verification

- Submitting three goals produces one active goal and two queued goals.
- Completing the active goal activates the next queued goal.
- Paused goals do not emit new tasks.
- Cancelled goals never resume unless resubmitted as a new goal.
