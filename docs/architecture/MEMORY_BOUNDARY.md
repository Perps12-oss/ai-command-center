# Memory Boundary

**Status:** Binding (ADR-020 Section 9 M1)  
**Authority:** ADR-020 Memory Architecture; ADR-015; ADR-005  
**Related:** ADR-008 (narrowed — derived views only)

---

## Canonical owners

| Domain | Authoritative owner | Notes |
|--------|---------------------|-------|
| Runtime / agent working state | **World Model** (entities, relationships, timeline, mutation journal) | Planning/replan should prefer WM + receipts |
| User / opt-in memory | **MemoryGraph** (SA `store_memory`) | ADR-015 |
| User-visible chat history | **Conversation repository** | UX transcript |
| Token-budget compaction | **Derived view only** | ADR-008 agent_visible summaries — never SoT |

## Non-canonical

- `ContextManager` truncation / short “Earlier conversation summary” strings — budget adapters, not memory SoT
- LLM hierarchical summaries — may exist as derived views; must not write MemoryGraph or WM as truth

## Replan context (ADR-019)

`plan.replan.request` carries `observations` (`execution.observation` facts). Summaries of chat are not a substitute for those structured observations.
