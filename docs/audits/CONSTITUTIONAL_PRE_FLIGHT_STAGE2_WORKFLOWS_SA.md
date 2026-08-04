# Constitutional Pre-Flight — Stage 2 Workflows → SA (SHADOW step 5a)

**Date:** 2026-08-04  
**Branch:** `cursor/stage2-workflows-sa-inventory-6855`  
**Baseline:** `origin/main` @ `e7732b9` (#130 Memory 4a)

## Continuity
- #129 ADR-012 A · #130 Memory soft-shadow 4a on main  
- Next: Workflows step **5a** inventory (no silent merge)

## Authority read
- [x] Constitution  
- [x] ADR-006 / ADR-012 A  
- [x] `SHADOW_SOT_INVENTORY.md` step 5  
- [x] `STATE_AUTHORITY_CONTRACT.md`  

## Scope
- Publish Workflows soft-shadow inventory  
- Update SHADOW / contract / guide / matrix  
- Pin tests: factory wires engine+persistence; SA has no workflow_lookup; mutate rejects workflow ops  

## Out of scope
- `workflow_lookup` on SA / `SA.mutate` for workflows  
- Retiring WorkflowEngine  
- Silent-merge runs into WM  
- Memory 4b Assembler rewire  

## Verdict
**GO**
