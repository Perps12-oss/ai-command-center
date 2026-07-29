# ADR-008: Conversation Context Compaction with Visibility Metadata

**Status:** Proposed  
**Date:** 2026-07-27  
**Deciders:** Architecture Review (Tom)  
**Supersedes:** —  
**Related:** `research/patterns/PAT-003.md`, `research/decisions/RD-001.md`, `docs/architecture/CHAT_MODERNIZATION_SPEC.md`

---

## Context

Long chat sessions exceed model context windows. Dropping messages blindly loses information shown to the user. `block/goose` preserves user-facing transcript while giving the model a compact summary by marking messages as `user_visible`/`agent_visible` and inserting summaries as `agent_visible` but `user_invisible`.

## Decision

Implement conversation context compaction as a `ConversationService` operation driven by `context.over_budget` events. Compaction preserves the user-visible transcript while replacing older model-visible messages with a structured summary.

### Contract

- `conversation.compaction_requested` — emitted when a token ratio threshold is exceeded.
- `conversation.compacted` — emitted with the new summary and visibility flags.
- `AppState` exposes `conversation_summary` and `compaction_status` for UI transparency.
- Original messages remain in the repository with `user_visible=true` and `agent_visible=false`.
- Summary message is stored with `user_visible=false` and `agent_visible=true`.
- The most recent user message is always preserved in the active context.

## Rationale

| Factor | Without compaction | With compaction |
|--------|--------------------|-----------------|
| Context overflow | Requests fail or are truncated | Summarized older context keeps recent turns |
| User transcript | Lost if messages are dropped | Preserved in repository and UI |
| Model context | Grows unbounded | Bounded by summary + recent turns |
| Trust | Opaque truncation | UI can show "earlier messages summarized" |

## Consequences

### Positive

- Avoids context-window failures.
- Keeps chat history coherent for the user.
- Reduces token spend on long sessions.

### Negative / Risk

- Summary quality depends on the model used.
- Summarization adds latency.
- Token counter must be accurate.

## Implementation Notes

- `ConversationService` subscribes to `context.over_budget`.
- Summarization uses a fast/cheap model tier (e.g., `summarize_model` from `SettingsSnapshot`).
- Token counting is delegated to a `TokenCounter` utility that aligns with the active provider's tokenizer.
- Compacted context is rebuilt from repository, not mutated in place, preserving an append-only history.

## Verification

- Unit test: compaction runs when token ratio exceeds threshold.
- Test: user-visible messages are not deleted.
- Test: summary is inserted with correct visibility metadata.
- Test: `AppState` reflects `conversation.compacted` event.
