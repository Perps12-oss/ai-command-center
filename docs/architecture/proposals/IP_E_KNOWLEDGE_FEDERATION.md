# IP-E — Knowledge Federation (SoT first)

**Status:** GATE 2 CLOSED 2026-08-14 — DEFER WITH CONDITION: live-wire read-only federation now, no embeddings/vector index. Decision: [`ADR-024`](../adr/ADR-024_KNOWLEDGE_FEDERATION_SOT.md).  
**Stream:** E  
**Parent ADR:** [ADR-020](../adr/ADR-020_MEMORY_ARCHITECTURE.md) **Accepted** (WM + MemoryGraph canonical; summaries derived). Federation/index is **not** decided.  
**UCGS:** `scope_embeddings` S5 still forbids embedding/vector DB **code** until profile enablement after Gate 2.  
**Baseline:** [STRATEGIC_GAP_MATRIX.md](../../audits/STRATEGIC_GAP_MATRIX.md) Stream E

---

1. **Problem.** Retrieval/federation without a SoT decision produces “the index knows it.” Need authoritative knowledge vs derived search.

2. **Exists.** World Model, MemoryGraph (ADR-015), conversation repository, ContextManager (no embeddings). `FederationService` unwired (not in `service_factory`). Entity `embedding_vector` column unused as SoT. No vector_store service on main. Historical Phase 8b unified-SoT/vectors **abandoned as a program**.

3. **Owning boundary.** Gate 2 must name SoT owners. Proposed layering (for ADR, not code):

```text
Authoritative State (WM / MemoryGraph / transcripts as today)
       ↓
Knowledge Projection (derived, rebuildable)
       ↓
Retrieval Index (derived; vector optional later)
       ↓
Semantic Search (capability)
       ↓
Context Assembly (ContextManager only)
```

4. **Remain authoritative.** ADR-020 surfaces. Indexes never become SoT. Inv 6 ContextManager. Inv 11.

5. **New behavior.** **After SoT ADR only:** federation interface (possibly live-wire read-only FederationService); indexing pipeline; embedding **abstraction**; retrieval; freshness/invalidation; provenance; source references; reconciliation. **Do not install a vector database in Gate 4 until Gate 2 explicitly allows a derived index and UCGS is updated.**

6. **Rejected.** Vector DB as memory; “ACC knows it because Chroma has it”; implementing Phase 8b checklists; silent use of `embedding_vector` as authority.

7. **Dependencies.** ADR-020/015; UCGS; Stream C (model for embeddings as capability); EventBus topics if federation goes live.

8. **Invariants.** Inv 11; Art. IX (no wrapper around SoT); UCGS S5 until enablement.

9. **Tests.** Stale index, deleted source, changed source, duplicates, provenance, retrieval failure, rebuild, authoritative consistency.

10. **Invalid if.** Search hit without source pointer; deleted WM node still “known”; ContextManager calls a vector vendor; factory-wired FederationService before ADR.

**Gate 2 ask:** New ADR-024+ — ACCEPT derived-index architecture **or** REJECT vectors and ACCEPT WM-only federation **or** DEFER WITH CONDITION (e.g. live-wire read-only federation without embeddings).
