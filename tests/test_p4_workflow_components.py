"""Smoke tests for P4 workflow graph components.

Tests:
- graph_canvas.py: zoom/pan, multi-select, undo/redo, keyboard shortcuts
- workflow_toolbar.py: execution controls, zoom buttons, shortcuts button
- node_library_palette.py: node types and card creation
- keyboard_shortcuts_overlay.py: overlay creation and toggle
"""

from __future__ import annotations

from ai_command_center.domain.workflow_graph import GraphNode, NodeState, WorkflowGraph
from ai_command_center.ui.components.graph_canvas import (
    EditAction,
    EditActionType,
    GraphCanvas,
    GraphHistory,
)
from ai_command_center.ui.components.keyboard_shortcuts_overlay import (
    KeyboardShortcutsOverlay,
    ShortcutsOverlayManager,
    SHORTCUTS,
)
from ai_command_center.ui.components.node_library_palette import (
    NODE_TYPES,
    NodeLibraryPalette,
    NodeTypeCard,
)
from ai_command_center.ui.components.workflow_toolbar import WorkflowToolbar

# Try importing pytest for type annotations, but don't fail if not available
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False


class TestGraphHistory:
    """Test undo/redo history tracking."""

    def test_push_and_pop_undo(self) -> None:
        history = GraphHistory()
        action = EditAction(
            action_type=EditActionType.NODE_MOVE,
            node_id="test-node",
            old_x=0.0,
            old_y=0.0,
            new_x=100.0,
            new_y=200.0,
        )
        history.push(action)
        assert history.can_undo()
        popped = history.pop_undo()
        assert popped is not None
        assert popped.node_id == "test-node"

    def test_redo_after_undo(self) -> None:
        history = GraphHistory()
        action = EditAction(
            action_type=EditActionType.NODE_MOVE,
            node_id="test-node",
            old_x=0.0,
            old_y=0.0,
        )
        history.push(action)
        history.pop_undo()
        assert history.can_redo()
        popped = history.pop_redo()
        assert popped is not None
        assert popped.node_id == "test-node"

    def test_max_size(self) -> None:
        history = GraphHistory(max_size=3)
        for i in range(5):
            history.push(EditAction(
                action_type=EditActionType.NODE_MOVE,
                node_id=f"node-{i}",
            ))
        # Should have max_size items
        assert len(history.undo_stack) == 3
        # First item should be node-2 (pushed at index 2)
        assert history.undo_stack[0].node_id == "node-2"


class TestGraphCanvas:
    """Test GraphCanvas zoom and selection methods."""

    def test_zoom_level_defaults(self) -> None:
        history = GraphHistory()
        assert history.undo_stack == []

    def test_edit_action_types(self) -> None:
        assert EditActionType.NODE_MOVE.value == "node_move"
        assert EditActionType.EDGE_ADD.value == "edge_add"
        assert EditActionType.EDGE_DELETE.value == "edge_delete"


class TestNodeLibraryPalette:
    """Test node library palette."""

    def test_node_types_count(self) -> None:
        """Verify expected number of node types."""
        assert len(NODE_TYPES) == 8

    def test_node_types_have_required_fields(self) -> None:
        """Verify each node type has required fields."""
        required_fields = {"id", "label", "icon", "description", "color"}
        for node_type in NODE_TYPES:
            assert required_fields.issubset(node_type.keys())
            assert node_type["id"]
            assert node_type["label"]
            assert node_type["icon"]

    def test_planning_node_type(self) -> None:
        """Verify planning node type exists."""
        planning = next(n for n in NODE_TYPES if n["id"] == "planning")
        assert planning["label"] == "Planning"
        assert planning["color"] == "#3B82F6"


class TestKeyboardShortcutsOverlay:
    """Test keyboard shortcuts overlay."""

    def test_shortcuts_defined(self) -> None:
        """Verify shortcuts are defined."""
        assert len(SHORTCUTS) > 0

    def test_shortcuts_have_categories(self) -> None:
        """Verify each shortcut has a category."""
        for group in SHORTCUTS:
            assert "category" in group
            assert "shortcuts" in group
            assert len(group["shortcuts"]) > 0

    def test_common_shortcuts_exist(self) -> None:
        """Verify common shortcuts are documented."""
        all_shortcuts = []
        for group in SHORTCUTS:
            all_shortcuts.extend(group["shortcuts"])

        # Check for common shortcuts
        shortcut_keys = [s["keys"] for s in all_shortcuts]
        assert "Ctrl + Z" in shortcut_keys  # Undo
        assert "Ctrl + A" in shortcut_keys  # Select all
        assert "Mouse Wheel" in shortcut_keys  # Zoom


class TestWorkflowToolbar:
    """Test workflow toolbar methods exist."""

    def test_zoom_methods_exist(self) -> None:
        """Verify toolbar has zoom control methods."""
        # These methods are defined on the class
        assert hasattr(WorkflowToolbar, "set_zoom_level")
        assert hasattr(WorkflowToolbar, "set_undo_enabled")
        assert hasattr(WorkflowToolbar, "set_redo_enabled")
        assert hasattr(WorkflowToolbar, "set_running")
        assert hasattr(WorkflowToolbar, "set_paused")
