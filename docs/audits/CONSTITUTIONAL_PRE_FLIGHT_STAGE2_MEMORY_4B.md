# Constitutional Pre-Flight — Stage 2 Memory 4b (Assembler → SA)

**Date:** 2026-08-04  
**Branch:** `cursor/stage2-memory-4b-assembler-sa-6855`  
**Baseline:** `origin/main` @ `7e9bc6c` (#131 Workflows 5a)

## Continuity
- #129 ADR-012 A · #130 Memory 4a · #131 Workflows 5a on main  
- Next: Memory **4b** — Assembler decision memory reads via SA

## Authority read
- [x] Constitution  
- [x] ADR-006  
- [x] `MEMORY_SOFT_SHADOW_INVENTORY.md` step 4b  
- [x] UI→AppState→EventBus→Services (Assembler is core helper; SA.query matches EA pattern)

## Scope
- Inject optional State Authority into `CapabilityContextAssembler`  
- When wired: memory graph snippets from `SA.query(include_memories=True)` — **no** `MEMORY_LOOKUP_REQUEST`  
- When unwired: keep sync bus cascade (tests / fallback)  
- Factory binds SA after construction  
- Update inventory / SHADOW / matrix  
- Tools `memory.query` remain capability fulfillment (4c)

## Out of scope
- `SA.mutate` for memory  
- Silent-merge memory ↔ WM  
- Workflows 5b  
- Retiring MGS bus topics entirely  

## Verdict
**GO**
