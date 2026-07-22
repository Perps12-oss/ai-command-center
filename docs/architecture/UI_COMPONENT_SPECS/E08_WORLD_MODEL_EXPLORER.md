# E08 — World Model Explorer

**Slice:** PR-UI-E08  
**Status:** Implemented on feature branch (pending merge)

## Purpose

Evolve `WorldExplorerView` with shared filters, graph filtering, and inspector selection — without replacing Phase 11B panels or inventing a second graph engine.

## Composition

```
WorldExplorerView
├── Hero (counts, New Entity → ENTITY_CREATE_REQUEST)
├── NodeFiltersBar (search / type / status / sort)
├── KnowledgeGraphPanel → WorldGraphCanvas (BaseGraphCanvas)
├── EntityExplorerPanel (list uses same NodeFilterState)
├── SelectionInspectorPanel
├── RelationshipExplorerPanel
└── MutationJournalPanel
```

## State

- Reads `AppState.world_model` only
- No new AppState fields (`selected_node_id` already on snapshot)

## Topics

| Topic | Intent |
|-------|--------|
| `ui.world.select` | Node focused |
| `ui.world.filter` | Filter bar changed |
| `ui.world.open` | Open world explorer |
| `world_model.node.selected` | Domain selection (reducer updates snapshot) |

Selection also publishes `UI_INSPECT_SELECT` for `world_node`.
