"""Tool registry contract."""

from __future__ import annotations

from typing import Any

from ai_command_center.core.tools import ToolSpec


class ToolRegistry:
    """Registers tools without executing them."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register_tool(self, tool_name: str | ToolSpec, metadata: dict[str, Any] | None = None) -> None:
        if isinstance(tool_name, ToolSpec):
            spec = tool_name
        else:
            details = metadata or {}
            handler = details.get("handler")
            if not callable(handler):
                return
            spec = ToolSpec(
                name=tool_name,
                description=str(details.get("description", tool_name)),
                handler=handler,
            )
        self._tools[spec.name] = spec

    def list_tools(self) -> list[str]:
        return sorted(self._tools)

    def describe_tool(self, tool_name: str) -> dict[str, Any] | None:
        spec = self._tools.get(tool_name)
        if spec is None:
            return None
        return {"name": spec.name, "description": spec.description}

    def get_spec(self, tool_name: str) -> ToolSpec | None:
        return self._tools.get(tool_name)
