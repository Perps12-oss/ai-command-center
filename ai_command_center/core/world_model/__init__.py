"""World model context compilation — dense structural snapshots for LLM prompts."""

from ai_command_center.core.world_model.context_compiler import (
    compile_entity_focus,
    compile_workspace_snapshot,
)
from ai_command_center.core.world_model.world_model import WorldModel, mutation_for_node

__all__ = [
    "WorldModel",
    "compile_entity_focus",
    "compile_workspace_snapshot",
    "mutation_for_node",
]
