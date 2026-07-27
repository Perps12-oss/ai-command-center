# ADR-009: Tool Confirmation Router Pipeline

**Status:** Proposed  
**Date:** 2026-07-27  
**Deciders:** Architecture Review (Tom)  
**Supersedes:** —  
**Related:** `research/patterns/PAT-004.md`, `research/decisions/RD-001.md`, `docs/architecture/ADR-004_RUNTIME_APPROVAL_MODEL.md`, `docs/architecture/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`

---

## Context

LLM-generated tool calls can be destructive, leak data, or repeat. ACC already has a runtime approval model (ADR-004), but it lacks a standardized mechanism for suspending a tool call, asking the user for explicit approval, and resuming with the user's decision. `block/goose` uses a `ToolConfirmationRouter` that registers pending requests and emits `action_required` messages.

## Decision

Introduce a **ToolConfirmationRouter** that is the single point for suspending tool execution and awaiting user approval. The router is invoked when an inspector or the permission service returns `RequireApproval`.

### Contract

- `tool.confirmation_required` — `ToolExecutorService` publishes this when a tool call must wait for user approval.
- `AppState` exposes `pending_tool_confirmations` so the UI can render an approval prompt.
- UI publishes `tool.approved` or `tool.denied` with the `tool_call_request_id`.
- On `tool.approved`, the router dispatches the original call through `ToolExecutorService`.
- On `tool.denied`, the router returns a synthetic tool result (error/refusal) so the model can recover.
- `permission.remembered` — when the user selects "always allow" / "never allow", `PermissionService` persists the per-tool level and emits this event.

## Rationale

| Factor | Without confirmation router | With confirmation router |
|--------|----------------------------|--------------------------|
| UX on dangerous calls | Executor blocks synchronously or fails | Clear `action_required` flow through `AppState` |
| Model recovery | Tool failure is opaque | Denied calls produce a structured response |
| Permission memory | One-shot allow/deny only | Per-tool remembered preferences |
| Authority | UI or executor may bypass approval | Centralized in `ToolExecutorService` + router |

## Consequences

### Positive

- User remains in control of destructive actions.
- `action_required` becomes a first-class event type.
- Permission preferences are persistent and revocable.

### Negative / Risk

- Adds an async suspension point in tool execution.
- If the router loses state, pending confirmations are orphaned; all state must be recoverable from repository/AppState.

## Implementation Notes

- `ToolConfirmationRouter` lives in `ai_command_center/services/tool_executor_service.py` or as a dedicated `tool_confirmation_service.py`.
- It uses an in-memory pending map keyed by `tool_call_request_id`; on crash, pending confirmations are rehydrated from `AppState` or marked failed.
- UI must render `pending_tool_confirmations` and publish approve/deny events.

## Verification

- Unit test: `RequireApproval` suspends execution until `tool.approved`.
- Test: `tool.denied` returns a synthetic failure message.
- Test: permission preference persists and short-circuits future confirmation.
- Architecture lint: no service other than `ToolExecutorService` dispatches a tool call.
