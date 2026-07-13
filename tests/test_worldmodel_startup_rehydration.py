"""Test WorldModel startup rehydration.

This test verifies that BrainRuntimeService publishes WORLD_MODEL_GRAPH_REFRESHED
on startup, which allows AppState.world_model to be populated without UI interaction.
"""

import unittest
from unittest.mock import MagicMock, patch
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import WORLD_MODEL_GRAPH_REFRESHED
from ai_command_center.domain.world_model import Node


class TestWorldModelStartupRehydration(unittest.TestCase):
    """Tests for WorldModel startup rehydration via BrainRuntimeService."""

    def test_brain_runtime_publishes_graph_refresh_on_load(self):
        """BrainRuntimeService should publish WORLD_MODEL_GRAPH_REFRESHED on startup."""
        from ai_command_center.core.app_state import AppStateStore
        
        bus = EventBus()
        store = AppStateStore(bus)  # Connect AppState to bus to capture events
        
        # Create a mock WorldModel
        mock_world_model = MagicMock()
        mock_world_model.recover.return_value = []
        mock_world_model._nodes = {
            "node-1": Node(id="node-1", type="task", attributes={"name": "Test Task"}),
        }
        mock_world_model.get_edges.return_value = []
        
        # Import and create BrainRuntimeService
        from ai_command_center.services.brain_runtime_service import BrainRuntimeService
        service = BrainRuntimeService(bus, mock_world_model)
        
        # Load the service (should trigger _publish_graph_refresh)
        service._on_load()
        
        # Verify the WorldModel recover was called
        mock_world_model.recover.assert_called_once()
        
        # Verify AppState received the event and populated world_model
        snap = store.snapshot
        self.assertEqual(len(snap.world_model.nodes), 1, 
            "WorldModelSnapshot should have 1 node after BrainRuntimeService startup")
        
        # Cleanup
        service._on_unload()
        store.close()

    def test_world_model_snapshot_populated_from_startup_event(self):
        """AppState.world_model should be populated after startup event."""
        from ai_command_center.core.app_state import AppStateStore
        
        bus = EventBus()
        store = AppStateStore(bus)
        
        # Simulate the startup event that would be published by BrainRuntimeService
        bus.publish(WORLD_MODEL_GRAPH_REFRESHED, {
            "nodes": [
                {"id": "entity-1", "type": "task", "label": "Task 1", "attributes": {}},
                {"id": "entity-2", "type": "concept", "label": "Concept 1", "attributes": {}},
            ],
            "edges": [
                {"id": "edge-1", "from_node_id": "entity-1", "to_node_id": "entity-2", 
                 "type": "related", "from_label": "Task 1", "to_label": "Concept 1"},
            ]
        }, source="brain_runtime")
        
        # Verify the snapshot is populated
        snap = store.snapshot
        self.assertEqual(len(snap.world_model.nodes), 2, 
            "WorldModelSnapshot should have 2 nodes after startup event")
        self.assertEqual(snap.world_model.node_count, 2)
        self.assertEqual(len(snap.world_model.edges), 1,
            "WorldModelSnapshot should have 1 edge after startup event")
        
        # Verify node IDs
        node_ids = {n.node_id for n in snap.world_model.nodes}
        self.assertEqual(node_ids, {"entity-1", "entity-2"})
        
        store.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
