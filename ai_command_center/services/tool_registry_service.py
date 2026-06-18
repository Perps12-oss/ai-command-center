"""Registered tools — lookup by name (Phase 4B)."""

from __future__ import annotations

from ai_command_center.core.tools import ToolSpec
from ai_command_center.services.base import BaseService


class ToolRegistryService(BaseService):
    """Holds ToolSpec definitions; executor resolves handlers here."""

    name = "tool_registry"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec
        self._bus.publish(
            "tool.registered",
            {"name": spec.name, "description": spec.description},
            source=self.name,
        )

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def _on_load(self) -> None:
        pass
