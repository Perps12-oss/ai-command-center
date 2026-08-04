# ADR-015: State Authority Mutate — Memory (`store_memory`)

**Status:** Accepted  
**Date:** 2026-08-04  
**Deciders:** Product / architecture (R1 next hard gate after ungated docs closeout)  
**Does not supersede:** ADR-005 (World Model), ADR-006 (ExecutionAuthority)  
**Related:** `STATE_AUTHORITY_CONTRACT.md`, `MEMORY_SOFT_SHADOW_INVENTORY.md` step **4d**  
**Baseline:** `origin/main` @ `7635585`

---

## Context

Stage 2 soft-shadow inventories closed Memory reads through State Authority
(`memory_lookup` → `lookup_for_state`) while writes stayed on
`MemoryGraphService` only. Contract R3 and the R1 stop line required a **new ADR**
before any non–World Model `SA.mutate`.

Without a receipted mutate path, decision-adjacent writers either:

- bypass SA and invent durable truth, or
- misuse WM `create_node` with `type=memory` as if it were `memory_nodes` SoT

Goals / workflows / executions remain higher dual-writer risk (scheduler / append-only
ownership). Memory already has one durable store and an SA read hook — safest first
non-WM mutate.

---

## Decision

**Accepted: State Authority may mutate Memory via a single op `store_memory`.**

Binding rules:

1. **Op shape**

   ```python
   {"op": "store_memory", "body": "label | content", "entity_id": optional}
   # workspace_id from StateDelta.workspace_id
   ```

2. **Sole durable write** goes through `MemoryGraphService.store_memory` →
   `MemoryRepository` / `memory_nodes` (same SoT as today’s capability tool).

3. **Receipt:** success fills `MutationReceipt.applied[]` (at least `op`,
   `mutation_id`, `memory_id`, `label`, `workspace_id`). Failures land in
   `message` / partial-apply rules unchanged from WM mutate.

4. **Hard forbid:** this op must **not** call `WorldModel.apply` or create WM
   nodes/edges for the same fact. WM `type=memory` echoes remain a separate
   orchestration concern — not this SoT.

5. **Still unsupported** on `SA.mutate` without a further ADR: goals, workflows,
   executions, agents, memory delete/merge, and any silent `memory_nodes` ↔ WM merge.

6. **Tools:** `memory.store` may remain a capability path that calls the same MGS
   method (soft dual to one SoT). It must not become a second durable store.

Live path:

```text
SA.mutate(store_memory)
  → memory_store callback (factory: MemoryGraphService.store_memory)
  → memory_nodes + MEMORY_STORED
  → MutationReceipt
```

---

## Consequences

| Area | Effect |
|------|--------|
| Contract | First non-WM mutate live; Memory disposition = **4d ✅** |
| Stop line | Next non-WM mutate domains still ADR-gated (goals/workflows/…) |
| Soft dual | Tools stay capability; decision writers should prefer SA.mutate |
| Tests | Soft-shadow pin flips from reject → ok + query round-trip |

---

## Out of scope

- Goals / workflows / executions / agents mutate  
- Delete-memory / merge into WM  
- Async EventBus / Goose / Predictive-Undo live wire  

---

## Verification

| Check | How |
|-------|-----|
| Factory wire | `memory_store=memory_graph.store_memory` |
| Op supported | `store_memory` in SA supported ops; WM apply not called |
| Round-trip | mutate → `SA.query(include_memories=True)` finds content |
| Other domains | workflows / executions / agents mutate still unsupported pins |
| Docs | Inventory 4d, contract, stop line, truth matrix updated |

---

## References

- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`  
- `docs/architecture/state_authority/MEMORY_SOFT_SHADOW_INVENTORY.md`  
- `docs/audits/R1_UNGATED_STOP_LINE.md`  
- `ai_command_center/services/state_authority_service.py`  
- `ai_command_center/services/memory_graph_service.py`  
- `ai_command_center/core/service_factory.py`  
