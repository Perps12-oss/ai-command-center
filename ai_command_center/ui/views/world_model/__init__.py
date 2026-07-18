"""World Model workspace panels (Phase 11B / Article 12)."""

from __future__ import annotations

from ai_command_center.ui.views.world_model.entity_explorer_panel import EntityExplorerPanel
from ai_command_center.ui.views.world_model.knowledge_graph_panel import KnowledgeGraphPanel
from ai_command_center.ui.views.world_model.mutation_journal_panel import MutationJournalPanel
from ai_command_center.ui.views.world_model.relationship_explorer_panel import (
    RelationshipExplorerPanel,
)
from ai_command_center.ui.views.world_model.selection_inspector_panel import (
    SelectionInspectorPanel,
)

__all__ = [
    "EntityExplorerPanel",
    "KnowledgeGraphPanel",
    "MutationJournalPanel",
    "RelationshipExplorerPanel",
    "SelectionInspectorPanel",
]
