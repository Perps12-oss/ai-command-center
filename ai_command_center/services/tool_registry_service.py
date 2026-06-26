"""Registered tools — lookup by name (Phase 4B)."""

from __future__ import annotations

from ai_command_center.core.events.topics import TOOL_REGISTERED
from ai_command_center.core.tools import ToolSpec
from ai_command_center.services.base import BaseService
from ai_command_center.tools.tool_registry import ToolRegistry


class ToolRegistryService(BaseService):
    """Holds ToolSpec definitions; executor resolves handlers through shared registry."""

    name = "tool_registry"

    def __init__(self, bus, registry: ToolRegistry | None = None) -> None:
        super().__init__(bus)
        self._registry = registry or ToolRegistry()

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    def register(self, spec: ToolSpec) -> None:
        self._registry.register_tool(spec)
        self._bus.publish(
            TOOL_REGISTERED,
            {"name": spec.name, "description": spec.description},
            source=self.name,
        )

    def get(self, name: str) -> ToolSpec | None:
        return self._registry.get_spec(name)

    def list_names(self) -> list[str]:
        return self._registry.list_tools()

    def _on_load(self) -> None:
        pass
