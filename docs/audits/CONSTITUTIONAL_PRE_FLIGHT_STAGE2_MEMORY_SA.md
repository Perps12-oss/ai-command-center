# Constitutional Pre-Flight — Stage 2 Memory → SA (SHADOW step 4 inventory)

**Date:** 2026-08-04  
**Branch:** `cursor/stage2-memory-sa-inventory-6855`  
**Baseline:** `origin/main` @ `97e3c80` (#129 ADR-012 A)

## Continuity
- Goals 3b Accept A on main (#129)
- Next: Memory soft-shadow inventory (no silent merge)

## Authority read
- [x] Constitution  
- [x] ADR-006 / ADR-012 A  
- [x] `SHADOW_SOT_INVENTORY.md` step 4  
- [x] `STATE_AUTHORITY_CONTRACT.md`  

## Scope
- Publish Memory soft-shadow inventory + migration plan  
- Update SHADOW / contract / guide / matrix (baseline SHA)  
- Pin tests: SA `memory_lookup` uses `lookup_for_state`; no bus side-effects; no memory mutate  

## Out of scope
- Rewire CapabilityContextAssembler / tools onto SA  
- `SA.mutate` for memory  
- Silent-merge `memory_nodes` ↔ World Model  
- Workflows step 5  

## Verdict
**GO**
