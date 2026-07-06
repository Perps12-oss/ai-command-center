"""Minimal MCP client interface for orchestration provider adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class McpServerConfig:
    """Configured MCP server endpoint (settings-backed stub)."""

    server_id: str
    command: str = ""
    args: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class McpToolCallResult:
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class McpClient(Protocol):
    """Skeleton MCP client — swap for SDK-backed implementation later."""

    def list_tools(self, server_id: str) -> tuple[str, ...]: ...

    def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> McpToolCallResult: ...


class StubMcpClient:
    """No-op MCP client used until real servers are configured."""

    def __init__(self, servers: dict[str, McpServerConfig] | None = None) -> None:
        self._servers = servers or {}

    def list_tools(self, server_id: str) -> tuple[str, ...]:
        if server_id not in self._servers:
            return ()
        return ("ping",)

    def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> McpToolCallResult:
        if server_id not in self._servers:
            return McpToolCallResult(success=False, error=f"unknown server: {server_id}")
        return McpToolCallResult(
            success=True,
            output={"server_id": server_id, "tool": tool_name, "arguments": arguments},
        )
