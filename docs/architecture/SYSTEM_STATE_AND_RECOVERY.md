# System State and Recovery

**Status:** Proposed Phase 0 contract, pending approval  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `docs/ARCHITECTURE.md`

## Purpose

The kernel must be a formal state machine, not an implicit collection of flags and conditionals.

This document defines allowed states, transitions, entry actions, exit actions, timeout behavior, and crash behavior for Brain v1.

## States

```text
BOOT
IDLE
PLANNING
EXECUTING
AWAITING_APPROVAL
PAUSED
RECOVERING
SHUTDOWN
```

## Transition table

| From | Allowed transitions | Trigger |
|------|---------------------|---------|
| `BOOT` | `RECOVERING`, `IDLE`, `SHUTDOWN` | startup check, recovery needed, fatal boot error |
| `RECOVERING` | `IDLE`, `SHUTDOWN` | journal replay complete, unrecoverable error |
| `IDLE` | `PLANNING`, `PAUSED`, `SHUTDOWN` | goal submitted, user pause, shutdown |
| `PLANNING` | `EXECUTING`, `PAUSED`, `IDLE`, `SHUTDOWN` | plan generated, pause, plan failed/no-op, shutdown |
| `EXECUTING` | `AWAITING_APPROVAL`, `IDLE`, `PAUSED`, `SHUTDOWN` | approval required, action complete, pause, shutdown |
| `AWAITING_APPROVAL` | `EXECUTING`, `IDLE`, `PAUSED`, `SHUTDOWN` | approved, denied/timeout, pause, shutdown |
| `PAUSED` | `IDLE`, `PLANNING`, `EXECUTING`, `SHUTDOWN` | resume to prior safe state, shutdown |
| `SHUTDOWN` | none | terminal state |

All other transitions are invalid and must publish a structured kernel error.

## Entry actions

### BOOT

- Initialize EventBus, AppState, repositories, and services through the composition root.
- Load settings snapshot.
- Open mutation journal.
- Decide whether recovery is required.

### RECOVERING

- Replay the last five mutations by default.
- Validate World Model cache consistency.
- Publish recovery progress events.
- Enter `IDLE` only after replay completes.

### IDLE

- Publish system readiness.
- Ask scheduler for the next goal only when a goal is queued.
- Keep observers running if enabled.

### PLANNING

- Build context with configurable token budget.
- Request plan generation.
- Validate plan shape and dependencies.
- Reject planner output that includes direct execution.

### EXECUTING

- Dispatch one action at a time.
- Enforce security tier.
- Apply successful mutations through runtime-owned `worldModel.apply()`.
- Emit action result with `CorrelationContext`.

### AWAITING_APPROVAL

- Present approval prompt through CLI or UI.
- Start 60-second timeout.
- Block only the pending action, not UI rendering.

### PAUSED

- Stop launching new actions.
- Preserve active goal, task, and correlation state.
- Allow safe cancellation or resume.

### SHUTDOWN

- Stop observers.
- Flush mutation journal.
- Stop services.
- Publish final telemetry and service state.

## Exit actions

| State | Exit actions |
|-------|--------------|
| `BOOT` | publish boot complete or boot failed |
| `RECOVERING` | record recovery summary |
| `IDLE` | record next goal correlation when leaving for planning |
| `PLANNING` | persist plan decision metadata |
| `EXECUTING` | persist action result |
| `AWAITING_APPROVAL` | persist approval decision or timeout |
| `PAUSED` | publish resume or shutdown decision |
| `SHUTDOWN` | none |

## Timeout behavior

- Approval timeout: 60 seconds, denies pending action.
- Planning timeout: configurable, default 120 seconds, fails the planning attempt.
- Execution timeout: action contract specific, required for every action.
- Recovery timeout: configurable, default 120 seconds, enters `SHUTDOWN` on failure.

Timeout events must include `CorrelationContext` when attached to a goal or action.

## Crash behavior

On restart:

1. Enter `BOOT`.
2. Detect unclean shutdown marker.
3. Enter `RECOVERING`.
4. Replay the last five mutation journal entries by default.
5. Rebuild in-memory World Model cache from repositories and journal.
6. Mark interrupted actions as failed or unknown; never mark them succeeded.
7. Return to `IDLE`.

Crash recovery must be deterministic and must not require planner or LLM calls.

## EventBus behavior

Proposed topics for Phase 1 contract registration:

```text
kernel.state_changed
kernel.transition_rejected
kernel.recovery_started
kernel.recovery_completed
kernel.timeout
```

All payloads require current state, target state when applicable, and `CorrelationContext` when available.

## Verification

- Invalid transitions are rejected and logged.
- Approval timeout moves from `AWAITING_APPROVAL` to `IDLE` or back to `EXECUTING` only according to action result.
- Unclean shutdown triggers `RECOVERING`.
- Recovery replays last five mutations and returns to `IDLE` without planner calls.
