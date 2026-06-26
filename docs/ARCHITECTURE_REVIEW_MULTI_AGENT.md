# Multi-Agent Runtime Architecture Review Gate

## Status

**Track 6.5 is gated until this review is completed and signed off.**

No multi-agent runtime code may be merged until the questions below are answered cleanly in this document.

## Constitutional questions

The multi-agent runtime design must explicitly answer how it complies with:

### A1 — Context Before Conversation

> How does the multi-agent runtime ensure that every agent has the correct context before it begins work, and how is that context assembled without violating ownership boundaries?

Required discussion:
- Which service owns context assembly for agents?
- How does an agent request context (EventBus topic, payload contract)?
- How does an agent receive the assembled context without direct repository access?
- What prevents an agent from bypassing `ContextManager` / context assembly?

### A2 — Execution Before Explanation

> How does the multi-agent runtime ensure that agents execute, produce, or validate something before they explain, narrate, or ask clarifying questions?

Required discussion:
- What is the minimum executable artifact an agent must produce before emitting a `chat.complete` or `ui.*` explanation?
- How are "thinking out loud" loops distinguished from "execution completed" events?
- What EventBus topics mark execution vs. explanation?

### A5 — Determinism Before AI

> How does the multi-agent runtime preserve deterministic, human-auditable execution paths and prevent AI-driven agents from becoming the primary execution path?

Required discussion:
- What are the deterministic fallback paths when an agent fails or refuses?
- Which commands are reserved for deterministic handlers and never routed to agents?
- How is agent output verified, versioned, or sandboxed before it can affect the workspace?
- How does the system prove that a given outcome could have been achieved without an agent?

## System-level question

### How does the multi-agent runtime avoid becoming the primary execution path?

> Multi-agent runtime must be an opt-in, high-level capability layer, not a hidden dependency of ordinary commands.

Required discussion:
- Which user intents explicitly trigger agent spawning?
- What is the default behavior when an agent-capable intent is received but the user has not opted in?
- How is the deterministic `CommandRouterService` protected from being shadowed by agent dispatch?
- What telemetry or audit trail proves that agent usage is a minority path?

## Ownership boundaries

The design must also confirm compliance with `AGENTS.md` v4:

```text
UI -> AppState -> EventBus -> Services -> Repositories -> Storage
```

In particular:
- No agent may access files, SQLite, settings, Ollama, or tools directly.
- Agents may only interact through `EventBus`, `AppState`, `SettingsService`, and repositories via services.
- No direct service-to-service calls.
- State must flow through `AppState` and `SettingsSnapshot`, not global variables.

## Required deliverables

Before the gate is lifted, the following must exist in this document:

1. Data-flow diagram for agent spawning, context assembly, execution, and result routing.
2. List of new EventBus topics and payloads (or confirmation that existing topics are sufficient).
3. Service decomposition diagram showing which existing services are used and which new services are introduced.
4. Explicit mapping of each constitutional question above to a concrete design decision.
5. List of forbidden execution paths (what agents are not allowed to do).
6. Verification plan: tests, scripts, and gates that prove the design is implemented as specified.

## Sign-off

- [ ] Author date
- [ ] Author name
- [ ] Reviewer name
- [ ] Constitutional compliance confirmed (yes / no)
- [ ] Recommendation: proceed to implementation, or revise design

## Notes

- A1, A2, and A5 refer to the constitutional principles of **Context Before Conversation**, **Execution Before Explanation**, and **Determinism Before AI**.
- This review is a prerequisite for any Track 6.5 implementation work.
