# Constitutional Pre-Flight — Stage 2 Slice 4 (Edge mutate + reconstruction)

**Date:** 2026-07-30  
**Branch:** `cursor/stage2-shadow-sot-goals-f84f`  
**Baseline:** Slice 3 Goals quarantine + #126 WM node mutate on path

## Authority documents read
- [x] `PROJECT_CONSTITUTION_V4.md`
- [x] `docs/architecture/STATE_AUTHORITY_CONTRACT.md` (R3 receipts, R5 reconstruction)
- [x] ADR-005 / ADR-006
- [x] `docs/architecture/SHADOW_SOT_INVENTORY.md`

## Scope
- Extend `StateAuthority.mutate` with `create_edge` / `delete_edge`
- Add `mutation_for_edge` helper on World Model
- Strengthen reconstruction acceptance: mutate nodes+edges → recover from journal (no chat) → `query` returns entities and relationships

## Out of scope
- GoalEngine domain merge / schema drop
- Memory / workflow mutate via SA
- Goose / Async EventBus

## Verdict
**GO**
