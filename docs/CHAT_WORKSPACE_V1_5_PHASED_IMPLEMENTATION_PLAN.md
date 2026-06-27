# Chat Workspace v1.5 — Phased Implementation Plan

## Objective
Deliver Chat Workspace v1.5 while preserving constitutional architecture and existing user-visible behavior unless explicitly approved.

## Scope Guardrails
- Keep ownership flow: UI -> AppState -> EventBus -> Services -> Repositories -> Storage.
- UI remains a renderer/intent publisher only.
- No direct service-to-service calls.
- No contract or topic mutation without governance update.
- ContextManager remains mandatory for all AI requests.

## Current Baseline
- UI surface: `ai_command_center/ui/views/chat_view.py`
- Chat orchestration: `ai_command_center/services/chat_handler_service.py`
- Presentation projection: `ai_command_center/core/app_state.py`
- Command ingress: `command.routed` (v1.0)
- Context contract: `ContextBundle` (v1.1)

## Phase 0 — Baseline Lock
### Goal
Capture current behavior and invariants before feature work.

### Tasks
- Record current event flow and expected chat lifecycle transitions.
- Capture baseline payload shapes for chat-related events.
- Snapshot current UI states for idle, streaming, cancel, error.

### Exit Criteria
- Baseline notes committed to docs.
- No code behavior changes in this phase.

### Verification
- `python scripts/verify_constitution.py`
- `python scripts/verify_contracts.py`

## Phase 1 — Event Contract Hardening
### Goal
Stabilize chat workspace event semantics for v1.5 features.

### Tasks
- Define explicit lifecycle markers for request begin, chunk, complete, cancel, and failure.
- Ensure payload consistency for `request_id`, status, source list, token estimate.
- Add defensive handling for missing or delayed upstream results.

### Exit Criteria
- No direct service calls introduced.
- Chat lifecycle events are deterministic and replayable from EventBus logs.

### Verification
- `python scripts/verify_constitution.py`
- `python scripts/verify_contracts.py`
- Targeted regression tests for chat lifecycle event ordering.

## Phase 2 — AppState Projection Expansion
### Goal
Expose full chat workspace presentation state through AppState.

### Tasks
- Extend reducers to track active request, stream status, and last assistant result summary.
- Keep state immutable and reducer-driven.
- Preserve existing fields and backward compatibility for current UI consumers.

### Exit Criteria
- UI can render all workspace states from AppState + local view state only.
- No repository or service references introduced into UI.

### Verification
- `python scripts/verify_constitution.py`
- AppState reducer tests for chat-specific transitions.

## Phase 3 — Chat UI v1.5 Integration
### Goal
Implement Chat Workspace v1.5 UX updates through AppState/EventBus only.

### Tasks
- Wire chat view updates from projected state and chat events.
- Preserve cancel/error/tool/system handling and loading history behavior.
- Keep UI logic presentation-only.

### Exit Criteria
- UI behavior stable under streaming, cancel, error, and history load flows.
- No direct service access from UI.

### Verification
- `python scripts/verify_constitution.py`
- UI interaction tests for idle/streaming/cancel/error/history states.

## Phase 4 — Reliability and Compatibility
### Goal
Harden for edge cases and migration safety.

### Tasks
- Add idempotency protections for duplicate events.
- Ensure stale request isolation (`request_id` ownership).
- Verify fallback behavior when model routing, notes, or memory lookups are delayed or absent.

### Exit Criteria
- Chat workspace handles out-of-order or partial event delivery safely.
- No contract version bump required unless explicitly approved.

### Verification
- `python scripts/verify_constitution.py`
- `python scripts/verify_contracts.py`
- Stress tests for cancel/timeout/retry scenarios.

## Phase 5 — Compliance Closeout
### Goal
Finalize governance and acceptance evidence.

### Tasks
- Update constitutional review with final impact notes.
- Update architecture/contracts docs only if materially changed.
- Record test evidence and residual risks.

### Exit Criteria
- Constitutional compliance marked COMPLETE.
- No unresolved architecture or contract violations.

### Verification
- `python scripts/verify_constitution.py`
- `python scripts/verify_contracts.py`
- Any phase-specific verify scripts touched by implementation.

## Risk Register
- Event fan-out race conditions across async publishers.
- Hidden UI coupling to service-local assumptions.
- Silent payload drift without contract verification.

## Deferred TODO
- Review pre-existing unrelated workspace change in ai_command_center/core/state/system_snapshot_builder.py (asdict publish payload update) after Chat Workspace v1.5 implementation review.

## Rollback Strategy
- Revert feature toggles to baseline chat lifecycle path.
- Preserve contract-compatible event payloads during rollback.
- Re-run constitution/contracts checks before release candidate promotion.

## Definition of Done
- Chat Workspace v1.5 shipped with constitutional invariants intact.
- All touched gates pass.
- Governance docs reflect final architecture and contract state.

## Implementation Progress
- Completed: Constitutional pre-flight and phase plan authoring.
- Completed: AppState chat lifecycle projection (`active_chat_request_id`, `chat_status`, `chat_streaming`, context sources/tokens, history count, terminal outputs/errors).
- Completed: UI stale request guards for chunk/complete/cancel/error handlers.
- Completed: UI context bar now reads AppState projection instead of chat_handler-specific `command.routed` payloads.
- Completed: Idempotent terminal event handling in UI for duplicate complete/cancel/error events and late chunk suppression when no active request.
- Completed: AppState reducers now ignore stale terminal events with request IDs when there is no active request and treat duplicate `chat.started` for the same request as idempotent.
- Completed: Added regression tests for stale terminal-event suppression and duplicate-start idempotency.
- Completed: Regression + governance checks (`unittest`, `verify_constitution.py`, `verify_contracts.py`) passing after each increment.
- Completed: Deeper Phase 3 reduction — `CHAT_STARTED` direct UI handler removed; chat start is now rendered from `AppState` (`chat_status=streaming`, `active_chat_request_id`, `last_command`).
- Completed: Added regression test `test_chat_start_projection_from_command_and_start` covering the AppState-driven chat start transition.
- Completed: Phase 4 increment — `CHAT_ERROR` events from `ChatHandlerService` now always carry `request_id`; pending state is cleaned up for early-error paths.
- Completed: Phase 4 increment — UI `CHAT_CHUNK` handler now filters against `AppState.active_chat_request_id` instead of local UI state for stale-request isolation.
- Completed: Added regression tests for stale `CHAT_ERROR` suppression and ChatHandler error `request_id` attribution.
- Completed: Phase 4 async/timeout/fallback restructuring of `ChatHandlerService` — now awaits upstream results (`memory.lookup.result`, `session.history.result`, `model.resolve.result`) before streaming, falls back to defaults after a configurable timeout, and handles `ui.chat_cancel` before stream start.
- Completed: Added stress tests for synchronous fast path, delayed model/memory fallback, and cancellation before stream start.
- Completed: Phase 4 — Reliability and Compatibility.
- Completed: Phase 5 — Compliance Closeout.
- Completed: Constitutional closeout document and ledger entry recorded.
- Completed: All constitutional, contract, and phase gates passing.
- Remaining: Deferred future work — retry policy for failed upstream results; stress scenarios for network-backed async upstream services if needed.
