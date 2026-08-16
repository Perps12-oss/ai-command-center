# ADR-024: Knowledge Federation SoT (Stream E — Gate 2)

**Status:** Accepted — DEFER WITH CONDITION (live-wire read-only federation; no embeddings/vector index yet)
**Gate 3 (Section 9 plan):** §9 — M1 read-only wiring only.
**Date:** 2026-08-14
**Deciders:** Owner (Gate 2), per `docs/governance/STRATEGIC_RUNTIME_PROGRAM.md`
**Related:** ADR-020 (Memory Architecture, parent), ADR-015 (SA Mutate Memory), Inv 6 (ContextManager), Inv 11 (single SoT), UCGS `scope_embeddings`
**Framework:** `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md` (Gate 2 decision on Integration Proposal, not a fresh multi-council review — the SoT-vs-index principle was already settled in ADR-020)
**Proposal:** [`IP_E_KNOWLEDGE_FEDERATION.md`](../proposals/IP_E_KNOWLEDGE_FEDERATION.md)
**Baseline:** `STRATEGIC_GAP_MATRIX.md` Stream E

---

## 1. Problem

ADR-020 already made World Model + MemoryGraph canonical and summaries derived. It did **not** decide whether ACC federates knowledge across a retrieval/index layer, and if so, whether that layer may ever include vectors/embeddings. Without that decision, `FederationService` sits unwired (not in `service_factory.py`), and the unused `embedding_vector` column on `Entity` is a latent dual-SoT risk: nothing stops a future PR from treating "the index found it" as "ACC knows it."

## 2. Decision

**DEFER WITH CONDITION.** This ADR authorizes exactly one thing now, and defers the rest:

**Authorized now:**
- Construct and wire the existing, already-implemented `FederationService` / `FederatedWorldModel` / `WorkspaceRegistry` into `service_factory.py` as a **read-only** capability over the current canonical stores (World Model, MemoryGraph, conversation repository). No new storage, no embeddings, no vector index.

**Deferred (not authorized by this ADR):**
- Any embedding generation, vector storage, or vector/semantic search. UCGS `scope_embeddings` **remains S5** (forbidden) — this ADR does **not** trigger profile enablement.
- Use of the existing `embedding_vector` column as anything other than an unused, non-authoritative fossil column. It must not be read or written by the read-only federation wiring authorized above.
- Any "index as SoT" pattern.

If a future need for semantic/vector search becomes concrete (not speculative), it requires its **own** proposal against the layering below, plus an explicit UCGS profile change — it is not pre-approved by this ADR.

## 3. SoT layering (binding for any future federation/retrieval work)

```text
Authoritative State   (World Model / MemoryGraph / conversation transcripts — unchanged from ADR-020)
       ↓
Knowledge Projection  (derived, rebuildable from authoritative state)
       ↓
Retrieval Index        (derived; vector is OPTIONAL and NOT authorized by this ADR)
       ↓
Semantic Search         (a capability, never a source of truth)
       ↓
Context Assembly       (ContextManager only — Inv 6 unchanged)
```

Any index, at any layer, is rebuildable from authoritative state and disposable without data loss. A deleted World Model node must not remain "known" via a stale index entry (see §5 invalid-if).

## 4. Remains authoritative / unchanged

- ADR-020 surfaces (World Model, MemoryGraph, conversation transcript) are unaffected.
- `ContextManager` remains the only AI context builder (Inv 6) — federation does not introduce a second context-assembly path.
- Inv 11 (single SoT) is unchanged: read-only federation is a **view**, not a new store.

## 5. Invalid if

- The read-only `FederationService` wiring authorized here writes to any store, generates embeddings, or calls a vector backend.
- A search/retrieval result is surfaced without a pointer back to its authoritative source (WM node, MemoryGraph entry, or transcript turn).
- A deleted or changed authoritative-state item still appears "known" through a stale federation read (the read path must reflect current state, not a cached snapshot that outlives its source).
- `embedding_vector` is read or written by any code path enabled by this ADR.

## 6. Tests (Gate 3 will scope exact suite)

Stale/deleted/changed source handling, duplicate handling, provenance (every result traces to a source), retrieval failure behavior, rebuild-from-scratch equivalence, and consistency with authoritative state at time of read.

## 7. Rejected (for now, not permanently)

- Installing any vector database or embedding pipeline as part of this Gate 2.
- Treating this ADR as blanket authorization for future semantic search — it is not; that requires its own proposal.
- Leaving `FederationService` permanently unwired — "exists but unwired" is the exact gap-matrix finding this ADR closes for the read-only case.

## 8. Next step

Gate 4 implementation against **§9** (read-only wiring only). Vector/embedding work stays gated behind a future proposal + UCGS profile change and is explicitly **not** unlocked by this ADR.

---

## 9. Gate 3 — Section 9 Implementation Plan (M1 — read-only federation)

Program Gate 3 for the **authorized slice only**. This is not embeddings, not a vector index, not a new SoT.

### Scope (M1)

Wire the existing `FederationService` / `FederatedWorldModel` / `WorkspaceRegistry` into `service_factory.py` as a **read-only view** over World Model, MemoryGraph, and the conversation repository.

| Field | Plan |
|-------|------|
| **Files** | `core/service_factory.py` (construct + `ServiceManager.register`); `services/federation_service.py`; `core/world_model/federation/federated_world_model.py`; `core/world_model/federation/workspace_registry.py`; `domain/federation.py`; existing topics in `core/events/topics.py`. **Do not** add `vector_store` / embedding services. |
| **Interfaces** | Existing: `federation.query.request` → `federation.query.result`; register/unregister + sync started/completed; `federation.conflict.detected`. Every result row **must** include a pointer to the authoritative source (WM node id, MemoryGraph entry id, or conversation/transcript turn id). |
| **Migrations** | None. Do not migrate, read, or write `Entity.embedding_vector`. Leave the column untouched. |
| **Wiring** | Factory owns construction (composition root). Federation talks to canonical stores through `FederatedWorldModel` only — no UI, no ContextManager fork (Inv 6 unchanged). EventBus for all inter-service traffic. |
| **Tests** | Extend `tests/test_federation.py` plus a factory/startup test that `create_application()` reports federation `READY`. Required cases from §6: stale/deleted/changed source no longer returned; duplicates; provenance present; query failure is explicit (empty result + error payload, not a fabricated hit); rebuild-from-scratch equivalence (registry reload); consistency with WM/Memory at read time. Arch-lint: no new service→service imports. |
| **Docs** | This section; `STRATEGIC_GAP_MATRIX.md` Stream E “unwired” becomes stale after Gate 4 — update in the implementation PR, not here. |
| **Acceptance** | Headless `create_application()` + `startup()` includes federation `READY`. A `FEDERATION_QUERY_REQUEST` returns sourced rows. No embedding call, no vector backend, UCGS `scope_embeddings` remains S5. |
| **Rollback** | Unregister from `service_factory.py`; leave classes and tests that construct the service directly. |
| **Invalid if** | Factory wiring writes any store; `embedding_vector` is read/written; search results lack provenance; a deleted WM node still “hits”; a second ContextManager path appears. |

**Not in M1:** `FEATURE_VECTOR_SEARCH`, Chromadb/Pinecone, semantic search product UI, UCGS profile enablement.

---

## References

- `docs/architecture/adr/ADR-020_MEMORY_ARCHITECTURE.md`
- `docs/architecture/adr/ADR-015_STATE_AUTHORITY_MUTATE_MEMORY.md`
- `ai_command_center/services/federation_service.py`
- `ai_command_center/core/service_factory.py`
- `ucgs.profiles/ai-command-center.yaml` (`scope_embeddings`)
- `docs/architecture/proposals/IP_E_KNOWLEDGE_FEDERATION.md`
