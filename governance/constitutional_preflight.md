# Constitutional Pre-Flight — Chat trust & feel (C5–C8)

**Branch:** `cursor/ui-c5-c8-chat-trust-4fb7`  
**Authority:** PROJECT_CONSTITUTION_V4.md

## Intent

1. **C5/C6** — New Chat creates a persisted conversation (no destructive
   `clear_messages` on the active id); conversation rail reads from
   `ConversationRepository` via EventBus → AppState (not UI-only SessionStore).
2. **C7+C3** — Fix assistant height cutoff (displaylines + scrollbar when capped);
   remove dead `AssistantBubble`/`UserBubble` path (docking/v2 blocks only).
3. **C8** — Shared `MSG_*` spacing constants for chat message packing.

## Invariants checked

| Invariant | Status |
|---|---|
| UI → AppState → EventBus → Services → Repositories → Storage | Preserved; New Chat / select via EventBus |
| UI isolation | Preserved; ConversationList remains display-only |
| Host supremacy | N/A |
| Contracts | New topics `chat.conversations_loaded`, `ui.chat.select_conversation` |

## Behaviour preservation

- Entity-scoped chats (`entity:…`) unchanged for open-chat
- Free-floating New Chat leaves prior conversation messages intact
- StreamTextBuffer / EmptyState / SystemStrip retained
