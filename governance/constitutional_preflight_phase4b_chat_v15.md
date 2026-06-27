# Phase 4B — ChatHandler Async/Fallback Restructuring Constitutional Pre-Flight

## Task Description

Continue Chat Workspace v1.5 Phase 4 by restructuring `ai_command_center/services/chat_handler_service.py` so it awaits upstream results (memory lookup, session history, model resolution) before streaming, while preserving the current synchronous behavior when those results are immediately available. The implementation must:

1. Collect upstream results asynchronously via EventBus events.
2. Fall back to defaults after a bounded timeout if any upstream result is delayed or absent.
3. Handle `UI_CHAT_CANCEL`/`CHAT_CANCELLED` while waiting so the request can be abandoned before streaming begins.
4. Keep all existing EventBus contracts unchanged.
5. Add targeted stress/regression tests for delayed results, timeout fallback, and cancellation before stream start.

## Authorities Reviewed

1. **PROJECT_CONSTITUTION_V4.md** — supreme authority; ownership flow, service lifecycle, no direct service-to-service calls.
2. **AGENTS.md** — implementation directives for coding agents.
3. **docs/ARCHITECTURE_ENFORCEMENT.md** — architecture rules (no direct service-to-service calls, repository pattern, service lifecycle).
4. **docs/ARCHITECTURE.md** — data flow, EventBus backbone, ContextManager mandate, service boundaries.
5. **docs/CONTRACTS.md** — locked contracts; no version changes planned.
6. **docs/CHAT_WORKSPACE_V1_5_PHASED_IMPLEMENTATION_PLAN.md** — Phase 4 scope and exit criteria.

## Files Reviewed

1. `ai_command_center/services/chat_handler_service.py` — chat orchestration.
2. `ai_command_center/services/memory_graph_service.py` — memory lookup result publisher.
3. `ai_command_center/services/session_service.py` — history result publisher.
4. `ai_command_center/services/model_router_service.py` — model resolution result publisher.
5. `ai_command_center/services/ollama_service.py` — streaming contract and stub.
6. `ai_command_center/core/event_bus.py` — thread-safe EventBus.
7. `ai_command_center/core/events/topics.py` — relevant topics.
8. `ai_command_center/core/context_manager.py` — ContextBundle and context budget.
9. `tests/test_chat_handler_phase4.py` — existing Phase 4 regression test.

## Protected Assets Impacted

### Tier A — Constitutional Assets

- **EventBus Architecture** — `ChatHandlerService` continues to communicate only via EventBus; no direct service calls.
- **Service Lifecycle** — `ChatHandlerService` remains a `BaseService`; the new request state machine respects `_on_load`/`_on_unload`.
- **ContextManager Contract** — every AI request still passes through `ContextManager.build_context()`.
- **Contract / Topic Registry** — no new topics or version changes; only tighter handling of existing `CHAT_ERROR`, `CHAT_CANCELLED`, and upstream result topics.

## Sources of Truth Impacted

- **Active chat request state** — `AppState.active_chat_request_id` remains the authoritative source; ChatHandler simply emits events that feed it.
- **Chat context assembly** — `ContextManager` remains the single source of truth for assembled prompts and token estimates.
- **Upstream results** — `memory.lookup.result`, `session.history.result`, `model.resolve.result` remain the authoritative sources for their respective data.

## Architectural Invariants Impacted

### Invariant 1 — Ownership Flow

**Status:** PRESERVED

Flow remains `UI -> AppState -> EventBus -> Services -> Repositories -> Storage`. `ChatHandlerService` only publishes and subscribes to EventBus events.

### Invariant 2 — UI Isolation

**Status:** PRESERVED

No changes to UI. UI continues to render from AppState and direct chunk events only.

### Invariant 3 — No Direct Service-to-Service Calls

**Status:** PRESERVED

`ChatHandlerService` will not call `memory_graph_service`, `session_service`, `model_router_service`, or `ollama_service` methods directly. It publishes requests and subscribes to results via EventBus, as it already does today.

### Invariant 4 — AppState Governance

**Status:** PRESERVED

`AppState` reducers are unchanged; the new service behavior only affects when and how `CHAT_STARTED`, `CHAT_ERROR`, and `CHAT_CANCELLED` are emitted.

### Invariant 8 — Topic Governance

**Status:** PRESERVED

No topic mutations. Existing topics used: `memory.lookup.request`, `memory.lookup.result`, `session.history.request`, `session.history.result`, `model.resolve.request`, `model.resolve.result`, `ui.chat.cancel`, `chat.cancelled`, `chat.error`, `chat.started`, `command.routed`, `context.snapshot_created`, `session.update.request`, `context.over_budget`, `context.trimmed`, `app.warning`.

### Invariant 11 — Source-of-Truth Integrity

**Status:** PRESERVED

No duplicate authority. `ChatHandlerService` remains the coordinator; it does not replace the upstream services or AppState.

## Contracts Impacted

- **command.routed v1.0** — unchanged; ChatHandler republishes with `status: "processing"` and `request_id` as before.
- **ContextBundle v1.1** — unchanged; still built from explicit caller-supplied context.
- **Chat lifecycle topics** — no version changes; payload shape unchanged.
- **OllamaService API v1.0** — unchanged; ChatHandler still calls `stream_chat(bundle, model, request_id)`.

## Gate Impact Assessment

- `python scripts/verify_constitution.py` — must pass.
- `python scripts/verify_contracts.py` — must pass.
- `python -m unittest tests.test_chat_handler_phase4 -v` — must pass; expanded with new stress tests.
- `python -m unittest tests.test_chat_workspace_v15 -v` — must pass.
- `python -m unittest discover -s tests -v` — must pass.
- Phase 1–3D gates — must continue to pass.

## Historical Gate Impact

No historical gates removed, bypassed, or weakened. The change is a service-internal refactor.

## Regression Risk

**Risk Level: MEDIUM**

Reasoning:
1. The change restructures the core chat orchestration flow.
2. Synchronous result paths must remain fast and behaviorally identical.
3. Timeout and cancellation paths introduce new concurrency.
4. Downstream UI and AppState logic is unchanged, reducing UI-layer risk.

Mitigation:
- Keep the existing synchronous fast path: if all results are available immediately, start streaming right away without waiting for the timeout.
- Default service timeout is 0.0s, so unconfigured standalone use remains synchronous and historical gates keep passing.
- The real application configures `upstream_timeout_seconds=1.0` to enable bounded async waiting for delayed upstream results.
- Use a daemon thread for the timeout, never a blocking wait on the EventBus thread.
- Protect request state with a per-request lock to prevent double-start or race between result handlers and timeout.
- Clean up request state on completion, cancellation, and timeout to prevent leaks.
- Expand `tests/test_chat_handler_phase4.py` with tests for:
  - synchronous fast path,
  - delayed model result fallback,
  - delayed memory result fallback,
  - cancellation before stream start.
- Run all unit tests and phase gates after implementation.

## Deferred Work

- Real async I/O for upstream services (e.g., network-backed memory or notes) is not introduced; only the ChatHandler becomes resilient to delayed synchronous results.
- Retry policy for failed upstream results is out of scope for this increment.

## Constitutional Status

**APPROVED**

Implementation may proceed.
