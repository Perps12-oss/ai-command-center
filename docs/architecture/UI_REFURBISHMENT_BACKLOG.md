# UI Refurbishment — Follow-on Backlog

**Status:** Active  
**Supersedes:** PR sequence in [archive/ACC_UI_REFURBISHMENT.md](archive/ACC_UI_REFURBISHMENT.md) (complete)  
**History:** [UI_REFURBISHMENT_AUDIT_STATUS.md](UI_REFURBISHMENT_AUDIT_STATUS.md)

The 15-PR UI Refurbishment program (PRs #49–#65) is merged. This backlog tracks
remaining debt and Slice 1b / hardening work only.

---

## P1 — Complete (PR timeline undo)

### Timeline undo handlers (`TIMELINE_UNDO_REQUEST`) — done

- [x] Topic + `timeline_service.undo()` publishes `undo_data`
- [x] Per-action handlers (`delete_entity`, `delete_relationship`, `remove_workspace_entity`)
- [x] Reversible timeline recording on entity/relationship/workspace bus operations
- [x] `TIMELINE_UNDO_RESULT` topic + tests

**Module:** `core/timeline/timeline_undo_handlers.py`

---

## P2 — Complete

### Workflow graph DAG

- [x] `WorkflowGraph.from_workflow_steps` DAG via `depends_on` / `next`
- [x] Layered layout (`core/workflow/workflow_graph_layout.py`)
- [x] `WorkflowDefinition` YAML load/dump

### Legacy inspector migration

- [x] `ExecutionInspector` passes `SpanItem`, `ArtifactItem`, `ProviderHealthSnapshot` to tabs

### Settings off-page projection

- [x] `state_applier._apply_settings_projection` syncs `SettingsView` on `settings_version`

---

## P3 — Slice 1b (COMPLETED 2026-07-10)

- [x] Canvas drag-and-drop (`UI_WORKFLOW_NODE_MOVE`, `GraphCanvas.on_node_move`)
- [x] Persisted workflow YAML (`domain/workflow_definition.py`)
- [x] `ApprovalNodeBadge` / `RetryVisualization` overlays on canvas
- [x] Full graph editing (add/remove edges, edge handles, context menu) — see `graph_canvas.py`
- [x] Workflow YAML import/export UI (toolbar buttons + file dialogs) — see `workflow_toolbar.py`
- [x] Library drop-to-canvas (partial — edge creation via node handle drag)

### Uncompleted

- [ ] Library palette drop-to-canvas for adding new nodes (not just edges)

---

## P3 — Documentation

- [x] Ownership dependency diagram in `docs/ARCHITECTURE.md`
- [x] Artifact viewer preview stubs for remaining kinds (improved with styled messages) — see `artifact_viewer.py`

---

## P4 — COMPLETED (2026-07-10)

The following UI work was implemented:

- [x] Node library palette with draggable node types — `node_library_palette.py`
- [x] Canvas zoom/pan controls — mouse wheel zoom, middle-click pan, toolbar buttons
- [x] Workflow execution controls (pause, resume, cancel) — toolbar buttons
- [x] Multi-select for nodes/edges — Ctrl+click, Shift+drag box select
- [x] Undo/redo for graph edits — Ctrl+Z/Y, toolbar buttons
- [x] Keyboard shortcuts overlay — ⌨ button in toolbar

---

## Governance

Track work as GitHub issues where possible. Run gates before merge:

```bash
python3 -m pytest -m "not slow"
python3 -m ruff check ai_command_center
python3 scripts/verify_constitution.py
python3 tools/ucgs_runner.py > .ucgs_last.yaml && python3 tools/ucgs_ci_gate.py .ucgs_last.yaml
```
