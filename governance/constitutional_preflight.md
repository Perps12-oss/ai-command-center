# Constitutional Pre-Flight — C8 chat density (real spacing fix)

**Branch:** `cursor/ui-c8-chat-density-4fb7`  
**Authority:** PROJECT_CONSTITUTION_V4.md

## Intent

Finish C8 properly: shared `MSG_*` tokens must (1) be referenced by
`chat_view` outer-row packs and (2) encode a denser scale than the pre-fix
16/14/10 wash — not merely rename literals.

## Invariants

UI isolation preserved; cosmetic spacing only; no EventBus/contract changes.
