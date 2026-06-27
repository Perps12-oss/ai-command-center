# Phase 3 — Chat Workspace v1.5 Integration Constitutional Pre-Flight

## Task Description

Complete Chat Workspace v1.5 Phase 3 by moving the chat-start rendering path in `ai_command_center/ui/app.py` from a direct `CHAT_STARTED` EventBus subscription to an AppState-driven projection. Streaming chunks, cancel/error/tool/system handling, and history loading remain event-driven. Targeted regression tests are added for the AppState start transition.

## Authorities Reviewed

1. **PROJECT_CONSTITUTION_V4.md** — supreme authority; ownership flow, UI isolation, AppState governance.
2. **AGENTS.md** — implementation directives for coding agents.
3. **docs/ARCHITECTURE_ENFORCEMENT.md** — architecture rules (UI isolation, no global state, no direct service calls).
4. **docs/ARCHITECTURE.md** — data flow, UI communication policy, state ownership.
5. **docs/CONTRACTS.md** — locked contracts; no version changes planned.
6. **docs/CHAT_WORKSPACE_V1_5_PHASED_IMPLEMENTATION_PLAN.md** — Phase 3 scope and exit criteria.

## Files Reviewed

1. `ai_command_center/ui/app.py` — chat event wiring and state application.
2. `ai_command_center/ui/views/chat_view.py` — presentation-only chat view.
3. `ai_command_center/core/app_state.py` — AppState reducers and chat projection fields.
4. `ai_command_center/core/events/topics.py` — chat lifecycle topics.
5. `ai_command_center/services/chat_handler_service.py` — chat service publishing `CHAT_STARTED`.
6. `ai_command_center/services/session_service.py` — history publisher.
7. `tests/test_chat_workspace_v15.py` — existing chat workspace state tests.

## Protected Assets Impacted

### Tier A — Constitutional Assets

- **EventBus Architecture** — `CHAT_STARTED` remains a canonical topic; the service-to-reducer flow is unchanged. Only the UI subscription is removed.
- **AppState Projection System** — chat-start presentation state is now consumed from AppState instead of the event payload.
- **UI Isolation** — no new backend or repository access introduced; UI continues to render from AppState and EventBus events.
- **Contract Registry / Topic Registry** — no contract or topic version changes.

## Sources of Truth Impacted

- **Chat presentation state** — source of truth remains `AppState` (`active_chat_request_id`, `chat_status`, `chat_streaming`).
- **Chat user prompt text** — derived from `AppState.last_command`, which is projected by the existing `command.routed` reducer.
- **Chat lifecycle topics** — no changes to canonical topics in `ai_command_center/core/events/topics.py`.

## Architectural Invariants Impacted

### Invariant 1 — Ownership Flow

**Status:** PRESERVED

Flow remains `UI -> AppState -> EventBus -> Services -> Repositories -> Storage`. UI now reads the chat start state from AppState instead of directly from the `CHAT_STARTED` event payload, strengthening the invariant.

### Invariant 2 — UI Isolation

**Status:** ENHANCED

UI no longer stores the pending chat prompt (`_pending_user_text`) as local business logic. The prompt is rendered from AppState projection.

### Invariant 4 — AppState Governance

**Status:** ENHANCED

AppState already owns `active_chat_request_id`, `chat_status`, and `chat_streaming`. The UI start transition is now driven exclusively by these fields.

### Invariant 8 — Topic Governance

**Status:** PRESERVED

`CHAT_STARTED` remains a canonical topic. No new topics or mutations.

### Invariant 11 — Source-of-Truth Integrity

**Status:** PRESERVED

No duplicate authority introduced. `command.routed` remains the authoritative source for the last user command text; `CHAT_STARTED` remains the authoritative source for the chat request ID.

## Contracts Impacted

- **command.routed v1.0** — read-only dependency; `AppState.last_command` is already projected from this event.
- **Chat lifecycle topics** — no version or payload changes.

## Gate Impact Assessment

- `python scripts/verify_constitution.py` — must continue to pass.
- `python scripts/verify_contracts.py` — must continue to pass; no contract version changes.
- `python -m unittest tests.test_chat_workspace_v15 -v` — must pass; additional regression test added for the start-from-state transition.

## Historical Gate Impact

No historical gates are removed, bypassed, or weakened. The change is scoped to the UI layer and uses existing AppState projection.

## Regression Risk

**Risk Level: LOW**

Reasoning:
1. No service, repository, or contract changes.
2. `CHAT_STARTED` event flow remains intact for AppState reducer and other subscribers.
3. Streaming chunk handling remains unchanged.
4. Cancel/error/tool/system behavior is unchanged.
5. The only UI behavior change is the source of the chat-start trigger (event payload -> AppState snapshot).
6. Idempotent duplicate-start protection is already provided by the AppState reducer.

Mitigation:
- Add a regression test for the AppState `last_command` + `active_chat_request_id` + `chat_status=streaming` start transition.
- Run the full chat workspace test suite and constitutional/contract gates after implementation.

## Constitutional Status

**APPROVED**

Implementation may proceed.
