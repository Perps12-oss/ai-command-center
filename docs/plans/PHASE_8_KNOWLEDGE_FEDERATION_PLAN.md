# Phase 8: Knowledge Federation

**Status:** FUTURE  
**Priority:** MEDIUM  
**Estimated Effort:** 6-8 weeks  
**Dependencies:** Phase 6 (External Bridge), Phase 7 (Multi-Agent)  
**Authority:** `PROJECT_CONSTITUTION_V4.md`

---

## Constitutional Note

**Vector DB / Embeddings require constitutional amendment.**

Current `ucgs.profiles/ai-command-center.yaml` forbids vectors without a constitutional phase gate. This phase assumes the amendment is ratified.

---

## Executive Summary

Implement cross-source knowledge federation enabling unified search across entities, notes, memory, and external sources (Obsidian vault, external APIs). This transforms the workspace from a collection of isolated data stores into a unified knowledge graph.

---

## Current State

**Implemented:**
- Memory graph service (`memory_graph_service.py`)
- Entity graph with relationships
- Obsidian integration (notes)
- Context compiler for prompt assembly

**Missing:**
- Cross-source unified search
- Knowledge graph visualization
- External source federation
- Vector-based similarity search (requires amendment)

---

## Architecture

### Knowledge Sources

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Knowledge Federation Layer                  │
├─────────────────────────────────────────────────────────────────┤
│  Entity Graph    │  Memory Graph   │  Notes    │  External APIs │
│  (entities/)     │  (memory_*)     │  (Obsidian)│  (future)     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Knowledge Query API │
                    │  knowledge.query    │
                    └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Unified Results    │
                    │  (ranked, filtered) │
                    └─────────────────────┘
```

### EventBus Topics

| Topic | Direction | Payload |
|-------|-----------|---------|
| `knowledge.query` | Inbound | `{ query, sources[], filters }` |
| `knowledge.results` | Outbound | `{ query, results[], scores[] }` |
| `knowledge.index.updated` | Outbound | `{ source, entity_ids[] }` |
| `knowledge.entity.linked` | Outbound | `{ source_entity, target_entity, relation }` |

---

## Implementation

### 8.1 Knowledge Query API

**File:** `ai_command_center/services/knowledge_query_service.py`

**Responsibilities:**
- Unified query interface across sources
- Result ranking and deduplication
- Filter application (entity type, date, workspace)

### 8.2 Cross-Source Index

**File:** `ai_command_center/services/knowledge_index_service.py`

**Responsibilities:**
- Maintain unified index across sources
- Incremental index updates on entity changes
- Index metadata (source, type, timestamp)

### 8.3 Graph Visualization

**File:** `ai_command_center/ui/views/knowledge_graph_view.py`

**Responsibilities:**
- Visualize knowledge graph (nodes + edges)
- Interactive exploration
- Filter and zoom controls

### 8.4 Vector Search (Post-Amendment)

**Files:**
```
ai_command_center/repositories/vector_store.py
ai_command_center/services/vector_search_service.py
```

**After constitutional amendment ratified.**

---

## Constitutional Amendment (Required)

### Proposed Amendment

```markdown
# AMEND-XXXX-VECTOR_CAPABILITY.md

## Article X — Vector Search Capability

Vector database and embedding capabilities are permitted under the following conditions:

1. **Opt-in only:** Vector search is disabled by default
2. **Local storage:** Vectors stored locally, not transmitted externally
3. **Privacy preserved:** No user data sent to third-party embedding services
4. **Fallback required:** Deterministic search as fallback when vectors unavailable
```

### Amendment Process

1. Submit `governance/amendment_template.md`
2. UCGS profile update for vector capability
3. Constitutional pre-flight review
4. Ratification vote

---

## Files

### Phase 8.1 (Before Amendment)

```
ai_command_center/services/knowledge_query_service.py
ai_command_center/services/knowledge_index_service.py
ai_command_center/ui/views/knowledge_graph_view.py
tests/test_knowledge_query_service.py
tests/test_knowledge_index.py
tests/test_knowledge_graph_view.py
```

### Phase 8.2 (Post-Amendment)

```
ai_command_center/repositories/vector_store.py
ai_command_center/services/vector_search_service.py
ai_command_center/services/embedding_service.py
tests/test_vector_search.py
tests/test_embedding_service.py
```

---

## Testing

### Unit Tests

- [ ] `test_knowledge_query_unified`
- [ ] `test_knowledge_index_updates`
- [ ] `test_cross_source_deduplication`

### Integration Tests

- [ ] `test_knowledge_graph_visualization`
- [ ] `test_obsidian_integration`
- [ ] `test_vector_search_accuracy` (post-amendment)

---

## Exit Criteria

- [ ] Unified knowledge query across all sources
- [ ] Graph visualization functional
- [ ] Cross-source search results ranked
- [ ] Constitutional amendment ratified (for vector search)
- [ ] Architecture lint clean
- [ ] UCGS PASS

---

## Non-Goals

- Cloud-based vector services
- Real-time sync with external sources
- Collaborative knowledge editing

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial plan |
