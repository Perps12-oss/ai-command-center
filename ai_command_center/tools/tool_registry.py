"""Tool registry contract."""

from __future__ import annotations

from typing import Any


class ToolRegistry:
    """Registers tools without executing them."""

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}

    def register_tool(self, tool_name: str, metadata: dict[str, Any]) -> None:
        self._tools[tool_name] = metadata

    def list_tools(self) -> list[str]:
        return sorted(self._tools)

    def describe_tool(self, tool_name: str) -> dict[str, Any] | None:
        return self._tools.get(tool_name)
