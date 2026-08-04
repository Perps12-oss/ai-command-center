# Memory Soft-Shadow Inventory (State Authority)

**Status:** ACTIVE — Stage 2 SHADOW step 4 (inventory + query-path pins)  
**Authority:** `STATE_AUTHORITY_CONTRACT.md`, ADR-006, `SHADOW_SOT_INVENTORY.md` step 4  
**Date:** 2026-08-04  
**Baseline:** `origin/main` @ `97e3c80` (#129)

## Verdict

Memory has **one durable store** (`MemoryRepository` / `memory_nodes`) owned by
`MemoryGraphService`, but **two decision-adjacent read paths**. Writes stay on
MGS. **Do not silent-merge** memory tables into World Model. **No `SA.mutate`
for memory** in this slice.

| Path | Stack | Decision reads? | Disposition |
|------|-------|:---------------:|-------------|
| **A — SA lookup (canonical for intake/planner)** | `SA.query` / `project` → `memory_lookup` → `MemoryGraphService.lookup_for_state` → `MemoryRepository.search` | ✅ EA / Planner | **keep / deepen** |
| **B — Parallel soft dual** | Assembler `MEMORY_LOOKUP_REQUEST` → MGS → `MEMORY_LOOKUP_RESULT`; tools `memory.query` / `memory.store` | ⚠️ chat/tools | Document; rewire later — **no silent kill** |

---

## Path A — State Authority (decision-facing)

```text
ExecutionAuthority.project / PlannerService
  → StateAuthorityService.query(include_memories=True)
  → memory_lookup(text, workspace_id=…)
  → MemoryGraphService.lookup_for_state   # no bus publish
  → MemoryRepository.search
  → StateContext.memories (+ STATE_CONTEXT_BUILT)
```

Evidence:

| Probe | Location |
|-------|----------|
| Factory wire | `service_factory.py` — `memory_lookup=memory_graph.lookup_for_state` |
| Query hook | `state_authority_service.py` — only when `include_memories` and non-empty text |
| Read-only helper | `memory_graph_service.lookup_for_state` — search only; no `MEMORY_*` publish |

---

## Path B — Soft dual (chat / tools / WM echo)

```text
CapabilityContextAssembler
  → MEMORY_LOOKUP_REQUEST → MGS → MEMORY_LOOKUP_RESULT → ContextManager

Tools (bind_state_capability_tools)
  → memory.query / memory.store → MGS.query_memory / store_memory
  → MEMORY_SELECTED / MEMORY_STORED (side effects)

OrchestrationService (on tool completion)
  → may write WM nodes type="memory"   # echo, not memory_nodes SoT
```

UI reads `AppState` projections only (R4). Direct `MemoryRepository` import from
UI/Planner is forbidden; production ownership stays MGS.

---

## Write authority

| Operation | Owner | Via SA? |
|-----------|-------|:-------:|
| Remember / store / delete | `MemoryGraphService` + repo | ❌ (until future mutate) |
| WM node `type=memory` | Orchestration / BrainRuntime | Separate graph — **not** memory SoT |

Hard rule: **no dual-write** of the same fact into `memory_nodes` and WM as if
they were one store.

---

## Migration plan (ordered)

| Step | Action | Gate |
|------|--------|------|
| **4a ✅** | Publish this inventory; pin SA lookup tests | This PR |
| 4b | Route Assembler decision snippets through SA `query` (or deprecate parallel lookup for decision class) | Follow-up slice |
| 4c | Keep tool `memory.query` as capability fulfillment; document it is not SA | Doc honesty |
| 4d | Optional later: `SA.mutate` memory ops with receipts — only after R1 clarity | Contract R3 |
| ❌ | Silent-merge `memory_nodes` ↔ WM entities | Forbidden |

---

## Related shadow SoT

| Domain | Status |
|--------|--------|
| WM nodes/edges | ✅ SA mutate/query |
| Goals | ✅ live scheduler; Phase-9 **RETIRED (ADR-012 A)** |
| Memory | ⚠️ soft dual reads — this document |
| Workflows | ⚠️ soft dual — this document (5a); 5b decide SA hooks vs execution-scoped |

---

## References

- `docs/architecture/SHADOW_SOT_INVENTORY.md`  
- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`  
- `ai_command_center/services/memory_graph_service.py`  
- `ai_command_center/services/state_authority_service.py`  
- `ai_command_center/core/service_factory.py`  
- `ai_command_center/orchestration/state_capability_tools.py`  
