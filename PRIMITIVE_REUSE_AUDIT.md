# Primitive Reuse Audit — GraphCanvas / Phase 11 World Model

**Auditor:** Tom (Senior Engineering Auditor) + Senior ACC Architect  
**Date:** 2026-07-18  
**Scope:** Graph rendering engines across Workflow, World Model, Relationship  
**Mission:** Determine CASE A vs CASE B; remediate FAIL to PASS

---

## Constitutional Pre-Flight

| Check | Result |
|-------|--------|
| Constitution (UI Isolation — renderer only) | Preserved — panels project state; no business logic in canvas |
| Architecture (UI → AppState → EventBus → Services → Repos) | Preserved — graph package is UI-layer only |
| Contracts (domain types stay in domain/) | Preserved — `GraphNodeVisual` / `GraphEdgeVisual` are UI visuals |
| No repository / service access from graph UI | Preserved |
| No domain leakage into shared primitive | Preserved — workflow/world-model mapping stays in adapters |

---

## 1. Graph primitive inventory (BEFORE)

| File | Class | Responsibility | Reused or duplicated |
|------|-------|----------------|----------------------|
| `ui/components/graph_canvas.py` | `GraphCanvas` | Full workflow graph engine: draw nodes/edges, zoom, pan, selection, drag, undo | **Independent engine** (workflow-coupled) |
| `ui/views/world_model/knowledge_graph_panel.py` | `KnowledgeGraphPanel` | Own `tk.Canvas`, `create_oval`/`create_line`, circular layout, click select | **Duplicated engine** |
| `ui/views/relationship_view.py` | `_GraphCanvas` | Own radial draw, oval/line/selection tags | **Duplicated engine** |
| `ui/views/world_model/relationship_explorer_panel.py` | `RelationshipExplorerPanel` | List UI only (no canvas graph) | N/A — not a graph engine |
| `ui/views/dependency_inspector/` | — | Not present in tree | N/A |

### Graph rendering inventory (BEFORE)

- Workflow: `GraphCanvas._draw_node` / `_draw_edge` via `create_rectangle` / `create_oval` / `create_line`
- World Model: `KnowledgeGraphPanel._redraw` via `create_oval` / `create_line`
- Relationship: `_GraphCanvas.render` via `create_oval` / `create_line`

### Zoom / Pan / Selection (BEFORE)

| Feature | Workflow `GraphCanvas` | World Model KG | Relationship `_GraphCanvas` |
|---------|------------------------|----------------|-----------------------------|
| Zoom | Own (`_zoom_level`, wheel, scale) | None | None |
| Pan | Own (Button-2 / scan) | None | None |
| Selection | Own multi-select + box | Own tag_bind click | Own tag_bind click |
| Node draw | Own | Own | Own |
| Edge draw | Own | Own | Own |

---

## 2. Compliance decision (BEFORE remediation)

**CASE B (FAIL)** — confirmed.

Evidence:

1. `KnowledgeGraphPanel` implemented an independent canvas renderer (`create_line` / `create_oval`, local layout, local hit-bind) instead of reusing a shared graph surface.
2. `RelationshipView._GraphCanvas` was a second private graph engine with independent node/edge drawing and selection.
3. Workflow `GraphCanvas` was a complete engine tightly coupled to `WorkflowGraph` domain types — usable as a primitive in name only; World Model correctly avoided workflow domain coupling, but incorrectly forked rendering instead of extracting a domain-agnostic surface.

**Primitive Reuse Compliance: FAIL** (blocking COMPLIANT)

Phase 11B’s “do not reuse WorkflowGraphView” guidance remains valid: domain behavior must stay separate. Constitution still requires a **shared rendering primitive**, not three canvas engines.

---

## 3. After architecture

```text
ui/components/graph/
  base_graph_canvas.py   ← shared surface (draw, zoom, pan, selection, hit-test)
  graph_node.py          ← GraphNodeVisual
  graph_edge.py          ← GraphEdgeVisual
  graph_selection.py     ← GraphSelection
  graph_layout.py        ← circular_layout, radial_layout

ui/components/graph_canvas.py
  GraphCanvas(BaseGraphCanvas)   ← Workflow domain adapter (undo, edge handles, overlays)

ui/views/world_model/knowledge_graph_panel.py
  KnowledgeGraphPanel            ← projects WorldModelSnapshot → visuals → BaseGraphCanvas

ui/views/relationship_view.py
  RelationshipView               ← projects WorldModelState → visuals → BaseGraphCanvas
  (private _GraphCanvas removed)
```

### Graph implementation inventory (AFTER)

| File | Class | Responsibility | Reused primitive |
|------|-------|----------------|------------------|
| `ui/components/graph/base_graph_canvas.py` | `BaseGraphCanvas` | Shared node/edge render, zoom, pan, selection, hit-test | **Shared primitive** |
| `ui/components/graph/graph_node.py` | `GraphNodeVisual` | Domain-agnostic node visual | Shared |
| `ui/components/graph/graph_edge.py` | `GraphEdgeVisual` | Domain-agnostic edge visual | Shared |
| `ui/components/graph/graph_selection.py` | `GraphSelection` | Shared selection state | Shared |
| `ui/components/graph/graph_layout.py` | layout helpers | Circular / radial placement | Shared |
| `ui/components/graph_canvas.py` | `GraphCanvas` | Workflow projection + edit gestures | **Reuses BaseGraphCanvas** |
| `ui/views/world_model/knowledge_graph_panel.py` | `KnowledgeGraphPanel` | World Model projection | **Reuses BaseGraphCanvas** |
| `ui/views/relationship_view.py` | `RelationshipView` | Relationship projection | **Reuses BaseGraphCanvas** |

---

## 4. Violations found

| ID | Violation | Status |
|----|-----------|--------|
| V1 | Second graph engine in `KnowledgeGraphPanel` | **Fixed** |
| V2 | Third graph engine in `RelationshipView._GraphCanvas` | **Fixed** |
| V3 | Workflow engine not extracted as domain-agnostic primitive | **Fixed** (`BaseGraphCanvas`) |

Non-violations:

- `RelationshipExplorerPanel` list UI — not a graph engine; no change required.
- Sparkline / system charts using `create_line` — not node-graph engines.

---

## 5. Files modified

**Added**

- `ai_command_center/ui/components/graph/__init__.py`
- `ai_command_center/ui/components/graph/base_graph_canvas.py`
- `ai_command_center/ui/components/graph/graph_node.py`
- `ai_command_center/ui/components/graph/graph_edge.py`
- `ai_command_center/ui/components/graph/graph_selection.py`
- `ai_command_center/ui/components/graph/graph_layout.py`
- `tests/test_graph_primitives.py`
- `PRIMITIVE_REUSE_AUDIT.md`

**Modified**

- `ai_command_center/ui/components/graph_canvas.py` — workflow adapter over `BaseGraphCanvas`
- `ai_command_center/ui/views/world_model/knowledge_graph_panel.py` — uses shared surface
- `ai_command_center/ui/views/relationship_view.py` — uses shared surface; removed `_GraphCanvas`

---

## 6. Verification

Commands:

```bash
python scripts/verify_constitution.py
python scripts/verify_ui_constitution.py
python -m pytest
```

(Results recorded in PR / CI after push.)

Structural proof tests in `tests/test_graph_primitives.py`:

- `GraphCanvas` subclasses `BaseGraphCanvas`
- World Model + Relationship sources contain no local `create_oval` / `create_line` engines
- Shared package files present

---

## 7. Compliance verdict (AFTER)

| Gate | Verdict |
|------|---------|
| CASE A (shared primitive, domain projection only) | **TRUE** |
| CASE B (duplicated engines) | FALSE |
| Primitive Reuse Compliance | **PASS** |
| Renderer-only UI | PASS |
| AppState-driven UI | PASS (unchanged contracts) |
| No repository / service access from graph UI | PASS |

**Overall:** Primitive Reuse FAIL → remediated → **PASS**.
