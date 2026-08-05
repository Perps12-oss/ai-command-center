# ADR-020: Memory Architecture

**Status:** Accepted — World Model canonical (summaries as derived views)  
**Date:** 2026-08-05  
**Deciders:** Multi-council Architecture Decision Framework  
**Related:** ADR-005, ADR-008 (narrowed), ADR-015, Inv 11  
**Framework:** `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`  
**Baseline:** `origin/main` @ `631b1f3`

---

## 1. Problem Statement

What should be ACC’s **canonical memory** for agent/runtime working context?

A common fix for context overflow is hierarchical LLM summarization (ADR-008-style compaction as the memory strategy). ACC already has World Model entities/relationships/timeline/journal and MemoryGraph as user-memory SoT. Treating narrative summaries as SoT risks drift and dual authorities.

---

## 2. Current Repository

| Fact | Evidence |
|------|----------|
| ContextManager | Truncation: keep last ~4 turns; ≤800-char join of truncated dropped turns; budget ~4000×0.70 — [`context_manager.py`](../../../ai_command_center/core/context_manager.py) |
| ADR-008 | **Proposed** — visibility-aware compaction; not implemented as that flow |
| MemoryGraph | Wired SoT for user memory via SA `store_memory` — ADR-015; [`memory_graph_service.py`](../../../ai_command_center/services/memory_graph_service.py) |
| World Model | Nodes/edges/mutations; journal replay — [`world_model.py`](../../../ai_command_center/core/world_model/world_model.py), [`world_model_repository.py`](../../../ai_command_center/repositories/world_model_repository.py) |
| Chat transcript | Conversation repository — user-visible history |
| Token counting | Heuristic `len//4`, not provider tokenizer |

**Status:** Budget truncation is a hack. WM + MemoryGraph are real SoTs. ADR-008 unimplemented.

---

## 3. Independent Review Proposal

Implement hierarchical summarization with importance weighting: pinned system/tools, working memory, episodic buffer, scratchpad. Compact every N turns or when fill &gt; 0.60. Preserve mutation events; summarize read-only turns via fast model; archive old summaries to SQLite with semantic retrieval. Treat summaries as the long-horizon memory strategy (ADR-008 full implement).

---

## 4. Architect Council

**Defense of Proposal A (hierarchical summaries as memory):**

- Context windows are finite; without compaction, long sessions fail or silently lose goals.
- Mutation-weighted summarization retains high-value turns better than uniform truncation.
- Visibility metadata (user_visible / agent_visible) preserves UX while shrinking model context.
- Industry chat products already ship summary-based memory; ACC ADR-008 already sketched it.
- Semantic archive enables cross-session recall without stuffing full transcripts.

---

## 5. Red Team

| Axis | Attack |
|------|--------|
| Assumptions | Assumes narrative text is the right SoT for agent state; WM already stores structured truth. |
| Scalability | Summary-of-summaries drift; embedding thresholds become silent correctness bugs. |
| Uniqueness | Chatbot memory pattern; Workspace OS centers entities/timeline, not essay memory. |
| Maintainability | LLM summarizer quality varies by tier; hard to test “correct” memory. |
| Production | Silent loss: model “remembers” false summary; user transcript diverges from agent belief. |
| SoT | Conflicts Inv 11 if summaries compete with MemoryGraph / WM. |

---

## 6. Alternative Architecture Team

**First principle:** Structured world state is memory; prose is a view.

```text
Canonical:
  World Model — entities, relationships, timeline, events, mutation journal
  MemoryGraph — user/opt-in memory SoT (ADR-015)
  Conversation repository — user-visible transcript

Derived (non-SoT):
  agent_visible compaction summaries (optional ADR-008-shaped views)
  ContextManager projections for a single LLM call
```

- Planning/replanning reads **WM checkpoints + receipts**, not only chat walls.
- Summaries may exist to fit token budgets but **never** become authoritative memory.
- Truncation today is acknowledged as temporary budget behavior, not identity.

---

## 7. Systems Review Board

| Criteria | A Summary SoT | B WM + derived views |
|----------|---------------|----------------------|
| Simplicity | 3 | 3 |
| Performance | 3 | 4 |
| Reliability | 2 | 5 |
| Local LLM | 2 | 5 |
| Testability | 2 | 5 |
| Extensibility | 3 | 5 |
| Uniqueness (Workspace OS) | 2 | 5 |
| Production Risk | 4 | 2 |

---

## 8. Constitution Guardian

| Question | Finding |
|----------|---------|
| More like every other assistant? | **A: Yes** — chat summary memory. |
| Erode Workspace OS? | **A: Yes** if entities/timeline yield to narrative. |
| Debt / dual SoT? | **A: High** vs MemoryGraph + WM. |
| Temporary as permanent? | Compaction as “fix overflow” becomes the memory architecture. |
| Inv 11 / ADR-015 / ADR-005? | **B required.** A conflicts unless summaries are explicitly non-authoritative. |

Guardian **requires Accept B**; ADR-008 may proceed only as derived-view.

---

## 9. Council Decision

**Accept B.**

1. Canonical runtime/agent memory for planning is **World Model** (entities, relationships, timeline, events, journal).
2. **MemoryGraph** remains user-memory SoT (ADR-015).
3. Conversation transcript remains user-visible history SoT for chat UX.
4. Hierarchical / visibility-aware summaries are **derived views** only — never SoT.
5. ADR-008 is **narrowed**: implementable as agent_visible compaction, not as ACC’s memory architecture.

---

## 10. Actionable Implementation Plan

| Milestone | Work | Tests / verification |
|-----------|------|----------------------|
| M1 | Document memory boundary: WM vs MemoryGraph vs chat transcript vs derived summary | Architecture doc section + truth matrix note |
| M2 | Planning/replan context builder prefers WM snapshot + recent receipts over truncated chat alone | Unit tests for context assembly |
| M3 | If ADR-008 proceeds: mark summaries `agent_visible` derived; never write summary as MemoryGraph/WM SoT | Tests that SoT writes reject summary-as-memory |
| M4 | Replace silent truncation narrative in docs; ContextManager remains budget adapter until M2 lands | Doc + existing context tests green |
| Out of scope | Embedding archive as SoT; replacing MemoryGraph with LLM summaries | — |

**Dependencies:** ADR-005, ADR-015, ADR-019 replan observations.  
**Migration:** No deletion of ContextManager; change what is considered authoritative.

---

## References

- `docs/architecture/adr/ADR-005_WORLD_MODEL_AUTHORITY.md`
- `docs/architecture/adr/ADR-008_CONVERSATION_COMPACTION.md`
- `docs/architecture/adr/ADR-015_STATE_AUTHORITY_MUTATE_MEMORY.md`
- `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`
