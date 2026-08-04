# Constitutional Pre-Flight — chat Phase 3 jank + ConversationRow click

**Branch:** `cursor/chat-phase3-row-fix-30d3`  
**Authority:** PROJECT_CONSTITUTION_V4.md

## Intent

1. Fix `_ConversationRow` click binding (`TypeError: lambda() missing '_'`) so
   conversation rail selection works under Tk/CustomTkinter on Python 3.14.
2. Stop chat Phase 3 from re-projecting inspector/timeline/chrome on every
   AppState tick — fingerprint-gate cosmetic chat updates (user logs:
   `Phase 3 (chat view) took 9994ms` then sustained ~1–1.5s).

## Invariants checked

| Invariant | Status |
|---|---|
| UI → AppState → EventBus → Services → Repositories → Storage | Preserved |
| UI isolation | Preserved — display/projection only |
| No new EventBus topics | N/A |

## Behaviour preservation

- Chat still projects history/conversations on revision change
- Inspector still updates when execution context / timeline revision changes
- Click-to-select still calls the same `on_select(session_id)` callback

## Out of scope

- Broader AppState notify reduction
- Markdown/message-block virtualization
