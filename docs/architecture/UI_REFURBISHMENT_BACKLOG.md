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

<<<<<<< HEAD
## P2 — Workflow graph DAG

- Non-linear `WorkflowGraph.from_workflow_steps` (true DAG, not linearized steps)
- Required before Slice 1b canvas editing

---

## P2 — Legacy inspector migration

- `ExecutionInspector` → typed payloads instead of dict feed to `inspector_*_tab.py`

---

## P2 — Settings off-page projection

- `state_applier` should project settings when view is not visible (minor)

---

## P3 — Slice 1b (explicitly deferred in original plan)

- Full drag-and-drop graph editing
- Branching / persisted workflow YAML
- `RetryVisualization` / `ApprovalNode` components
=======
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

## P3 — Slice 1b (partial)

- [x] Canvas drag-and-drop (`UI_WORKFLOW_NODE_MOVE`, `GraphCanvas.on_node_move`)
- [x] Persisted workflow YAML (`domain/workflow_definition.py`)
- [x] `ApprovalNodeBadge` / `RetryVisualization` overlays on canvas
- [ ] Full graph editing (add/remove edges, library drop-to-canvas)
- [ ] Workflow YAML import/export UI
>>>>>>> origin/main

---

## P3 — Documentation

<<<<<<< HEAD
- [ ] Ownership dependency diagram in `docs/ARCHITECTURE.md` (AGENTS.md deliverable)
=======
- [x] Ownership dependency diagram in `docs/ARCHITECTURE.md`
>>>>>>> origin/main
- [ ] Artifact viewer preview stubs for remaining kinds

---

## Governance

Track work as GitHub issues where possible. Run gates before merge:

```bash
python3 -m pytest -m "not slow"
python3 -m ruff check ai_command_center
python3 scripts/verify_constitution.py
python3 tools/ucgs_runner.py > .ucgs_last.yaml && python3 tools/ucgs_ci_gate.py .ucgs_last.yaml
```
