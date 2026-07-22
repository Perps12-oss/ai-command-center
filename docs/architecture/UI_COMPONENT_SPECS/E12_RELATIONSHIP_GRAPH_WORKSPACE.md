# E12 — Relationship Graph Workspace

**Slice:** PR-UI-E12  
**Status:** Implemented on feature branch (pending merge)

## Purpose

Full-graph workspace for the World Model: all nodes/edges, shared filters/search, selection inspector, and double-click navigation into World Explorer.

## Composition

```
GraphWorkspaceView
├── Hero (metrics + Open World Explorer)
├── NodeFiltersBar (shared E08 filters)
├── KnowledgeGraphPanel (WorldGraphCanvas / BaseGraphCanvas)
├── SelectionInspectorPanel
└── RelationshipExplorerPanel
```

## State

- Reads `AppState.world_model` only
- No new AppState fields
- No mutable `WorldModelState` listeners in the new workspace

## Topics

| Topic | Intent |
|-------|--------|
| `ui.graph.select` | Node focused |
| `ui.graph.filter` | Filter / search update |
| `ui.graph.open` | Open graph workspace |
| `ui.graph.navigate` | Double-click → navigate (default `world_explorer`) |

Selection also publishes domain `WORLD_MODEL_NODE_SELECTED` and `UI_INSPECT_SELECT` kind `world_node`.

## Reuse rules

- Must use `BaseGraphCanvas` / `WorldGraphCanvas` / `KnowledgeGraphPanel` — no second graph engine
- Must reuse `NodeFiltersBar`, `SelectionInspectorPanel`, `RelationshipExplorerPanel`
- Legacy `RelationshipView` (`relationships` route) remains unchanged
