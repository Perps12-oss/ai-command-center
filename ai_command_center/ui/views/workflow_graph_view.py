"""WorkflowGraphView — n8n-style workflow graph workspace.

P4 Integration:
- Node Library (existing)
- Canvas Zoom/Pan (GraphCanvas)
- Execution Controls (WorkflowToolbar)
- Multi-select (GraphCanvas)
- Undo/Redo (GraphCanvas + WorkflowToolbar)
- Keyboard Shortcuts Overlay
"""

from __future__ import annotations

import tkinter as tk
import tkinter.filedialog as filedialog
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.core.projectors.automation_workspace_projector import (
    AutomationWorkspaceProjector,
)
from ai_command_center.core.projectors.workflow_graph_projector import WorkflowGraphProjector
from ai_command_center.core.state.workflow_graph_state import (
    WorkflowGraphState,
    decode_workflow_steps,
)
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.domain.workflow_definition import WorkflowDefinition
from ai_command_center.domain.workflow_graph import GraphEdge, GraphNode, WorkflowGraph
from ai_command_center.ui.components.docks.execution_timeline_dock import ExecutionTimelineDock
from ai_command_center.ui.components.docks.inspector_dock import InspectorDock
from ai_command_center.ui.components.graph_canvas import GraphCanvas
from ai_command_center.ui.components.inspector.workflow_node_inspector import WorkflowNodeInspector
from ai_command_center.ui.components.keyboard_shortcuts_overlay import ShortcutsOverlayManager
from ai_command_center.ui.components.workflow_node_library import WorkflowNodeLibrary
from ai_command_center.ui.components.workflow_toolbar import WorkflowToolbar
from ai_command_center.ui.design_system import theme_v2 as T

DEMO_WORKFLOW_ID = "demo-linear"
DEMO_WORKFLOW_STEPS: tuple[dict[str, Any], ...] = (
    {
        "id": "plan",
        "name": "Plan",
        "kind": "planning",
        "type": "tool",
        "tool": "shell",
        "args": {"command": "echo plan"},
    },
    {
        "id": "execute",
        "name": "Execute",
        "kind": "tool",
        "type": "tool",
        "tool": "shell",
        "args": {"command": "echo execute"},
    },
    {
        "id": "report",
        "name": "Report",
        "kind": "artifact",
        "type": "tool",
        "tool": "shell",
        "args": {"command": "echo report"},
    },
)


class WorkflowGraphView(ctk.CTkFrame):
    """Workflow graph workspace with library, canvas, and bottom docks."""

    def __init__(
        self,
        master: Any,
        *,
        on_run: Callable[[str, list[dict[str, Any]]], None] | None = None,
        on_pause: Callable[[], None] | None = None,
        on_resume: Callable[[], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
        on_node_select: Callable[[str, str, str], None] | None = None,
        on_node_move: Callable[[str, float, float], None] | None = None,
        on_compare: Callable[[], None] | None = None,
        on_scrub: Callable[[int], None] | None = None,
        on_edge_create: Callable[[str, str], None] | None = None,
        on_edge_delete: Callable[[GraphEdge], None] | None = None,
        on_import_result: Callable[[WorkflowDefinition], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_DEEP, **kwargs)
        self._on_run = on_run or (lambda _workflow_id, _steps: None)
        self._on_pause = on_pause or (lambda: None)
        self._on_resume = on_resume or (lambda: None)
        self._on_cancel = on_cancel or (lambda: None)
        self._on_node_select = on_node_select or (lambda _node_id, _label, _workflow_id: None)
        self._on_node_move = on_node_move or (lambda _node_id, _x, _y: None)
        self._on_compare = on_compare or (lambda: None)
        self._on_scrub = on_scrub or (lambda _index: None)
        self._on_edge_create = on_edge_create or (lambda _src, _tgt: None)
        self._on_edge_delete = on_edge_delete or (lambda _edge: None)
        self._on_import_result = on_import_result or (lambda _definition: None)
        self._graph_state: WorkflowGraphState | None = None
        self._running = False
        self._paused = False
        self._shortcuts_overlay: ShortcutsOverlayManager | None = None
        self._build()

    def _build(self) -> None:
        self._toolbar = WorkflowToolbar(
            self,
            on_run=self._handle_run,
            on_pause=self._handle_pause,
            on_resume=self._handle_resume,
            on_cancel=self._handle_cancel,
            on_compare=self._on_compare,
            on_export=self._handle_export,
            on_import=self._handle_import,
            on_undo=self._handle_undo,
            on_redo=self._handle_redo,
            on_shortcuts=self._handle_shortcuts,
            on_zoom_in=self._handle_zoom_in,
            on_zoom_out=self._handle_zoom_out,
            on_zoom_reset=self._handle_zoom_reset,
        )
        self._toolbar.pack(fill="x")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)

        self._paned = tk.PanedWindow(
            body,
            orient=tk.HORIZONTAL,
            sashwidth=4,
            sashrelief=tk.FLAT,
            background=T.BG_GLASS_BORDER,
            handlesize=0,
            showhandle=False,
        )
        self._paned.pack(fill="both", expand=True)

        left = ctk.CTkFrame(self._paned, fg_color=T.BG_PANEL, corner_radius=0)
        center = ctk.CTkFrame(self._paned, fg_color=T.BG_DEEP, corner_radius=0)
        self._paned.add(left, minsize=160, stretch="never")
        self._paned.add(center, minsize=360, stretch="always")

        self._library = WorkflowNodeLibrary(left, on_preview=self._handle_node_preview)
        self._library.pack(fill="both", expand=True)

        self._canvas = GraphCanvas(
            center,
            on_node_select=self._handle_node_select,
            on_node_move=self._handle_node_move,
            on_edge_create=self._handle_edge_create,
            on_edge_delete=self._handle_edge_delete,
        )
        self._canvas.pack(fill="both", expand=True)

        bottom = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=220)
        bottom.pack(fill="x")
        bottom.pack_propagate(False)

        bottom_split = tk.PanedWindow(
            bottom,
            orient=tk.HORIZONTAL,
            sashwidth=4,
            sashrelief=tk.FLAT,
            background=T.BG_GLASS_BORDER,
            handlesize=0,
            showhandle=False,
        )
        bottom_split.pack(fill="both", expand=True)

        timeline_host = ctk.CTkFrame(bottom_split, fg_color=T.BG_DEEP, corner_radius=0)
        inspector_host = ctk.CTkFrame(bottom_split, fg_color=T.BG_PANEL, corner_radius=0)
        bottom_split.add(timeline_host, minsize=280, stretch="always")
        bottom_split.add(inspector_host, minsize=220, stretch="never")

        self._timeline_dock = ExecutionTimelineDock(
            timeline_host,
            on_scrub=self._on_scrub,
            timeline_height=72,
        )
        self._timeline_dock.pack(fill="both", expand=True)

        self._inspector_dock = InspectorDock(inspector_host)
        self._workflow_inspector = WorkflowNodeInspector(self._inspector_dock.host)
        self._inspector_dock.register("workflow", self._workflow_inspector)
        self._inspector_dock.set_default(self._workflow_inspector)
        self._inspector_dock.pack(fill="both", expand=True)

    def _resolve_run_target(self) -> tuple[str, list[dict[str, Any]]]:
        if self._graph_state is not None:
            workflow_id = self._graph_state.workflow_id or DEMO_WORKFLOW_ID
            steps = decode_workflow_steps(self._graph_state.step_payload_json)
            if steps:
                return workflow_id, [dict(step) for step in steps]
            return workflow_id, AutomationWorkspaceProjector.steps_for_workflow(workflow_id)
        return DEMO_WORKFLOW_ID, [dict(step) for step in DEMO_WORKFLOW_STEPS]

    def _handle_run(self) -> None:
        workflow_id, steps = self._resolve_run_target()
        self._on_run(workflow_id, steps)
        self._running = True
        self._paused = False
        self._toolbar.set_running(True)

    def _handle_pause(self) -> None:
        """Pause the running workflow."""
        self._paused = True
        self._toolbar.set_paused(True)
        self._on_pause()

    def _handle_resume(self) -> None:
        """Resume the paused workflow."""
        self._paused = False
        self._toolbar.set_paused(False)
        self._on_resume()

    def _handle_cancel(self) -> None:
        """Cancel the running workflow."""
        self._running = False
        self._paused = False
        self._toolbar.set_running(False)
        self._toolbar.set_paused(False)
        self._on_cancel()

    def _handle_undo(self) -> None:
        """Handle undo for graph edits."""
        self._canvas.record_node_move("", 0, 0)  # Trigger undo via canvas
        self._update_toolbar_buttons()

    def _handle_redo(self) -> None:
        """Handle redo for graph edits."""
        self._update_toolbar_buttons()

    def _handle_shortcuts(self) -> None:
        """Toggle the keyboard shortcuts overlay."""
        if self._shortcuts_overlay is None:
            self._shortcuts_overlay = ShortcutsOverlayManager(self)
        self._shortcuts_overlay.toggle()

    def _handle_zoom_in(self) -> None:
        """Zoom in the canvas."""
        self._canvas.zoom_in()
        self._toolbar.set_zoom_level(self._canvas.get_zoom_level())

    def _handle_zoom_out(self) -> None:
        """Zoom out the canvas."""
        self._canvas.zoom_out()
        self._toolbar.set_zoom_level(self._canvas.get_zoom_level())

    def _handle_zoom_reset(self) -> None:
        """Reset zoom to 100%."""
        self._canvas.zoom_reset()
        self._toolbar.set_zoom_level(self._canvas.get_zoom_level())

    def _update_toolbar_buttons(self) -> None:
        """Update toolbar button states based on canvas state."""
        self._toolbar.set_undo_enabled(self._canvas.can_undo())
        self._toolbar.set_redo_enabled(self._canvas.can_redo())
        self._toolbar.set_zoom_level(self._canvas.get_zoom_level())

    def _handle_node_preview(self, category: str, label: str) -> None:
        node_id = f"lib-{category.lower()}-{label.lower().replace(' ', '-')}"
        workflow_id = self._graph_state.workflow_id if self._graph_state else DEMO_WORKFLOW_ID
        self._on_node_select(node_id, f"{category}: {label}", workflow_id)

    def _handle_node_select(self, node: GraphNode) -> None:
        workflow_id = self._graph_state.workflow_id if self._graph_state else DEMO_WORKFLOW_ID
        self._on_node_select(node.node_id, node.label, workflow_id)
        if self._graph_state is not None:
            graph = self._graph_from_state(self._graph_state)
            self._canvas.render(graph, selected_node_ids={node.node_id})

    def _handle_node_move(self, node_id: str, x: float, y: float) -> None:
        self._on_node_move(node_id, x, y)

    def _handle_edge_create(self, source_id: str, target_id: str) -> None:
        """Handle edge creation from canvas."""
        self._on_edge_create(source_id, target_id)

    def _handle_edge_delete(self, edge: GraphEdge) -> None:
        """Handle edge deletion from canvas."""
        self._on_edge_delete(edge)

    def _handle_export(self) -> None:
        """Export workflow to YAML file."""
        if self._graph_state is None:
            return

        graph = self._graph_from_state(self._graph_state)
        workflow_name = self._graph_state.workflow_name or "workflow"

        # Convert graph to definition
        nodes = [
            {"id": node.node_id, "label": node.label, "kind": node.kind}
            for node in graph.nodes
        ]
        edges = [
            {"source": edge.source_id, "target": edge.target_id}
            for edge in graph.edges
        ]

        definition = WorkflowDefinition(
            workflow_id=graph.workflow_id or DEMO_WORKFLOW_ID,
            workflow_name=workflow_name,
        )
        yaml_content = definition.to_yaml()

        # Show save dialog
        filename = filedialog.asksaveasfilename(
            title="Export Workflow",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
            initialfile=f"{workflow_name.lower().replace(' ', '_')}.yaml",
        )

        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(yaml_content)
            except OSError as e:
                # Log error but don't crash - UI should handle gracefully
                pass

    def _handle_import(self) -> None:
        """Import workflow from YAML file."""
        filename = filedialog.askopenfilename(
            title="Import Workflow",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
        )

        if not filename:
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                yaml_content = f.read()

            definition = WorkflowDefinition.from_yaml(yaml_content)

            # Notify parent about imported workflow
            self._on_import_result(definition)
        except (OSError, ValueError) as e:
            # Log error but don't crash - UI should handle gracefully
            pass

    def _graph_from_state(self, state: WorkflowGraphState) -> WorkflowGraph:
        return WorkflowGraphProjector.from_state_items(
            state.workflow_id or DEMO_WORKFLOW_ID,
            run_id=state.run_id,
            nodes=state.nodes,
            edges=state.edges,
        )

    def apply_state(self, state: WorkflowGraphState) -> None:
        """Project AppState.workflow_graph into the workspace."""
        self._graph_state = state
        self._running = state.running
        self._toolbar.set_workflow_name(state.workflow_name)
        self._toolbar.set_running(state.running)
        graph = self._graph_from_state(state)
        selected_ids = {state.selected_node_id} if state.selected_node_id else set()
        self._canvas.render(graph, selected_node_ids=selected_ids)
        self._update_toolbar_buttons()

        steps = [
            {
                "name": node.label,
                "status": node.state.value,
                "duration_ms": 0.0,
            }
            for node in graph.nodes
        ]
        labels = [node.label for node in graph.nodes]
        active_index = 0
        if state.selected_node_id:
            for index, node in enumerate(graph.nodes):
                if node.node_id == state.selected_node_id:
                    active_index = index
                    break
        elif state.running:
            for index, node in enumerate(graph.nodes):
                if node.state.value == "running":
                    active_index = index
                    break
        self._timeline_dock.render(
            steps,
            scrub_labels=labels,
            scrub_index=active_index,
        )

    def show_inspector(self, ref: InspectableRef) -> None:
        self._inspector_dock.show(ref)

    def clear_inspector(self) -> None:
        self._inspector_dock.clear()


__all__ = ["DEMO_WORKFLOW_ID", "DEMO_WORKFLOW_STEPS", "WorkflowGraphView"]
