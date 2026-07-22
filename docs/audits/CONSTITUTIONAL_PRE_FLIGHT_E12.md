# Constitutional Pre-Flight — PR-UI-E12 Relationship Graph Workspace

**Slice:** PR-UI-E12 — Relationship Graph Workspace  
**Baseline:** `origin/main` @ `8608864` (post-E11 #101)  
**Builder:** Cursor (sole coder + Tom auditor)

---

## Authority checks

- [x] Constitution / UI Constitution Art. 12 + Art. 21
- [x] ADR — reuse `BaseGraphCanvas` / `WorldGraphCanvas` / `KnowledgeGraphPanel` (no second engine)
- [x] Compose `SelectionInspectorPanel` (do not fork)
- [x] AppState `world_model` only — no mutable `WorldModelState` in new workspace
- [x] Roadmap E12

---

## Scope

1. Add `ui/components/world_model/graph_renderer.py` — projection helpers
2. Add `GraphWorkspaceView` — full graph + filters/search + double-click navigate
3. Extend `KnowledgeGraphPanel` with `on_activate` (double-click)
4. Register `graph_workspace` + `UI_GRAPH_*`
5. Tests under `tests/ui/views/test_graph_workspace_view.py`

No E13. Keep legacy `RelationshipView` intact.

---

## AppState

- Fields added: **none**

---

## Pre-flight verdict

**GO**
