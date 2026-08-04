# Memory Soft-Shadow Inventory (State Authority)

**Status:** ACTIVE — Stage 2 SHADOW steps 4a–4d closed (ADR-015)  
**Authority:** `STATE_AUTHORITY_CONTRACT.md`, ADR-006, ADR-015, `SHADOW_SOT_INVENTORY.md` step 4  
**Date:** 2026-08-04  
**Baseline:** `origin/main` @ ADR-015 acceptance tip

## Verdict

Memory has **one durable store** (`MemoryRepository` / `memory_nodes`) owned by
`MemoryGraphService`. Decision reads go through SA (`memory_lookup`). Decision
writes may go through **`SA.mutate(store_memory)`** (ADR-015 / 4d) or the
capability tool `memory.store` — both call the same MGS method. **Do not
silent-merge** memory tables into World Model.

| Path | Stack | Decision reads/writes? | Disposition |
|------|-------|:----------------------:|-------------|
| **A — SA lookup (canonical for intake/planner/chat assembly)** | `SA.query` / `project` → `memory_lookup` → `MemoryGraphService.lookup_for_state` → `MemoryRepository.search`; Assembler uses SA when bound (4b) | ✅ EA / Planner / Assembler | **keep** |
| **A′ — SA mutate (ADR-015)** | `SA.mutate(store_memory)` → `memory_store` → `MemoryGraphService.store_memory` → `memory_nodes` + receipt | ✅ receipted write | **4d ✅** |
| **B — Parallel soft dual** | Unbound Assembler `MEMORY_LOOKUP_REQUEST` → MGS; tools `memory.query` / `memory.store` | ⚠️ tools / unbound tests | Tools stay capability; same SoT as A′ |

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

## Path A′ — SA mutate (ADR-015 / 4d)

```text
Caller
  → StateAuthorityService.mutate(StateDelta(operations=[{op: store_memory, body, …}]))
  → memory_store(body, workspace_id=delta.workspace_id, entity_id=…)
  → MemoryGraphService.store_memory → memory_nodes + MEMORY_STORED
  → MutationReceipt.applied[]   # never WorldModel.apply
```

Hard rule: **no dual-write** of the same fact into `memory_nodes` and WM as if
they were one store.

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
| Remember / store | `MemoryGraphService` + repo | ✅ `store_memory` (ADR-015) |
| Delete | `MemoryGraphService` + repo | ❌ (until further ADR) |
| WM node `type=memory` | Orchestration / BrainRuntime | Separate graph — **not** memory SoT |

---

## Migration plan (ordered)

| Step | Action | Gate |
|------|--------|------|
| **4a ✅** | Publish this inventory; pin SA lookup tests | #130 |
| **4b ✅** | Route Assembler memory snippets through SA `query` | Factory binds SA; bus lookup fallback when unbound |
| **4c ✅** | Keep tool `memory.query` as capability fulfillment; **not** SA | Doc honesty (closeout) |
| **4d ✅** | `SA.mutate` `store_memory` with receipts (no WM dual-write) | **ADR-015** |
| ❌ | Silent-merge `memory_nodes` ↔ WM entities | Forbidden |

### 4c honesty — tools vs SA

| Surface | Authority |
|---------|-----------|
| `SA.query(include_memories=True)` + Assembler bind | State Authority read path |
| `SA.mutate(store_memory)` | State Authority write path (ADR-015) |
| Capability / tool `memory.query` / `memory.store` | **Capability fulfillment** — same MGS SoT; **must not** mutate WM as memory SoT |

---

## Related shadow SoT

| Domain | Status |
|--------|--------|
| WM nodes/edges | ✅ SA mutate/query |
| Goals | ✅ live scheduler; Phase-9 **RETIRED (ADR-012 A)**; mutate still deferred |
| Memory | ✅ 4a–4d — this document + ADR-015 |
| Workflows | ✅ 5a+5b execution-scoped; mutate deferred |

---

## References

- `docs/architecture/adr/ADR-015_STATE_AUTHORITY_MUTATE_MEMORY.md`  
- `docs/architecture/SHADOW_SOT_INVENTORY.md`  
- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`  
- `ai_command_center/services/memory_graph_service.py`  
- `ai_command_center/services/state_authority_service.py`  
- `ai_command_center/core/service_factory.py`  
- `ai_command_center/orchestration/state_capability_tools.py`  
