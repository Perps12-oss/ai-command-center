"""Registered tools — lookup by name (Phase 4B)."""

from __future__ import annotations

from ai_command_center.core.events.topics import TOOL_STARTED, TOOL_RESULT, TOOL_ERROR
from ai_command_center.core.tools import ToolSpec
from ai_command_center.services.base import BaseService
from ai_command_center.tools.tool_registry import ToolRegistry


class ToolRegistryService(BaseService):
    """Holds ToolSpec definitions; executor resolves handlers here."""

    name = "tool_registry"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._tools: dict[str, ToolSpec] = {}
        self._registry = ToolRegistry()

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec
        self._registry.register_tool(spec.name, {"description": spec.description, "name": spec.name})
        self._bus.publish(
            TOOL_STARTED,
            {"name": spec.name, "description": spec.description},
            source=self.name,
        )

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def _on_load(self) -> None:
        pass
