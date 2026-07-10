# Runtime Safety

**Status:** Proposed Phase 0 contract, pending approval  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `docs/ARCHITECTURE.md`, `docs/architecture/VNEXT_STATE_DRIVEN_BLUEPRINT.md`

## Purpose

Runtime executes approved actions and is the only component allowed to call `worldModel.apply()`.

Planner outputs intent. Scheduler selects work. Runtime performs gated execution. World Model records truth.

## Security tiers

```text
READ
  Examples: list files, read metadata, search notes
  Approval: automatic when initiated by user or trusted scheduled workflow

WRITE
  Examples: create file, modify note, update workspace entity
  Approval: user confirmation when action affects user data outside ACC metadata

WRITE_DESTROY
  Examples: delete file, overwrite content, destructive move, irreversible external change
  Approval: explicit approval required
```

Security tier belongs to the action contract. Runtime must reject actions without a declared tier.

## Approval v1

Approval is local and single-user.

Interfaces:

```text
IApprovalGate
  request_approval(request: ApprovalRequest) -> ApprovalDecision
  cancel_approval(approval_id: string, correlation: CorrelationContext) -> void

ApprovalRequest
  id: string
  action_id: string
  tier: READ | WRITE | WRITE_DESTROY
  summary: string
  details: object
  timeout_seconds: int
  correlation: CorrelationContext

ApprovalDecision
  approval_id: string
  approved: bool
  reason: string
  decided_at: datetime
  correlation: CorrelationContext
```

Implementation v1:

- CLI prompt or UI popup.
- Timeout is 60 seconds.
- Timeout denies the action.
- Denied and timed-out actions publish explicit events.

## Action result contract

```text
ActionResult
  action_id: string
  status: succeeded | failed | cancelled | denied | timed_out
  output: object
  error: RuntimeErrorRecord?
  correlation: CorrelationContext
```

`ActionResult` is required for runtime logs, EventBus publications, and mutation journal entries.

## Error taxonomy

```text
RuntimeErrorRecord
  code: validation_error | approval_denied | approval_timeout | permission_error | capability_unavailable | execution_failed | world_model_apply_failed | transient_io
  message: string
  retry_hint: none | retry_same | retry_after_delay | revise_goal | request_approval
  details: object
  correlation: CorrelationContext
```

Runtime must include a retry hint. Retry behavior remains conservative in v1: no automatic retry for `WRITE` or `WRITE_DESTROY`.

## EventBus behavior

Proposed topics for Phase 1 contract registration:

```text
runtime.action_started
runtime.approval_requested
runtime.approval_decided
runtime.action_completed
runtime.action_failed
runtime.action_denied
runtime.world_model_apply_requested
runtime.world_model_apply_completed
```

All payloads require `CorrelationContext`.

## World Model mutation rule

Runtime is the only component that calls `worldModel.apply()`.

```text
Planner -> plan.generated
Scheduler -> task.ready
Runtime -> action execution -> worldModel.apply()
World Model -> mutation journal -> AppState projection
```

Observers, planners, capabilities, and UI never mutate the World Model directly.

## Verification

- `WRITE_DESTROY` action cannot run without explicit approval.
- Approval timeout denies the action after 60 seconds.
- Planner output cannot call `worldModel.apply()`.
- Runtime emits `ActionResult` with the same `CorrelationContext` received from the goal.
- Failed World Model apply creates a failed action result and does not pretend success.
