"""Minimal MCP client interface for orchestration provider adapter."""

from __future__ import annotations

import asyncio
import json
import subprocess
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


@dataclass(frozen=True, slots=True)
class McpServerStatus:
    """Status of an MCP server connection."""

    server_id: str
    connected: bool
    last_error: str | None = None
    tools: tuple[str, ...] = ()


class MCPServerConnection:
    """Manages a connection to an MCP server via stdin/stdout JSON-RPC."""

    def __init__(self, config: McpServerConfig) -> None:
        self._config = config
        self._process: subprocess.Popen[bytes] | None = None
        self._request_id = 0
        self._tools: list[str] = []
        self._connected = False

    @property
    def server_id(self) -> str:
        return self._config.server_id

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def tools(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def connect(self) -> bool:
        """Start the MCP server process."""
        try:
            cmd = [self._config.command, *self._config.args]
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**self._config.env},
            )
            self._connected = True
            self._discover_tools()
            return True
        except FileNotFoundError:
            self._connected = False
            return False
        except Exception:  # noqa: BLE001
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Stop the MCP server process."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        self._connected = False
        self._tools.clear()

    def _discover_tools(self) -> None:
        """Query the server for available tools."""
        response = self._send_request("tools/list", {})
        if response and "tools" in response:
            self._tools = [t.get("name", "") for t in response["tools"] if "name" in t]

    def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> McpToolCallResult:
        """Call a tool on the MCP server."""
        if not self._connected or not self._process:
            return McpToolCallResult(success=False, error="Not connected")

        try:
            response = self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments,
            })

            if response.get("isError"):
                return McpToolCallResult(
                    success=False,
                    error=response.get("content", [{}])[0].get("text", "Unknown error"),
                )

            return McpToolCallResult(
                success=True,
                output=response.get("content", [{}])[0].get("text", ""),
            )
        except Exception as e:  # noqa: BLE001
            return McpToolCallResult(success=False, error=str(e))

    def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Send a JSON-RPC request and wait for response."""
        if not self._process:
            return None

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        try:
            self._process.stdin.write(json.dumps(request).encode() + b"\n")
            self._process.stdin.flush()

            response_line = self._process.stdout.readline()
            if not response_line:
                return None

            response = json.loads(response_line.decode())
            return response.get("result", {})
        except (json.JSONDecodeError, IOError, OSError):
            return None


class McpClient(Protocol):
    """Skeleton MCP client — swap for SDK-backed implementation later."""

    def list_tools(self, server_id: str) -> tuple[str, ...]: ...

    def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> McpToolCallResult: ...

    def get_status(self, server_id: str) -> McpServerStatus | None: ...


class StubMcpClient:
    """No-op MCP client used until real servers are configured."""

    def __init__(self, servers: dict[str, McpServerConfig] | None = None) -> None:
        self._servers = servers or {}
        self._connections: dict[str, MCPServerConnection] = {}

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

    def get_status(self, server_id: str) -> McpServerStatus | None:
        if server_id not in self._servers:
            return None
        return McpServerStatus(server_id=server_id, connected=True, tools=("ping",))


class MCPServerPool:
    """Manages multiple MCP server connections."""

    def __init__(self) -> None:
        self._connections: dict[str, MCPServerConnection] = {}

    def add_server(self, config: McpServerConfig) -> bool:
        """Add and connect a server."""
        conn = MCPServerConnection(config)
        if conn.connect():
            self._connections[config.server_id] = conn
            return True
        return False

    def remove_server(self, server_id: str) -> None:
        """Disconnect and remove a server."""
        if server_id in self._connections:
            self._connections[server_id].disconnect()
            del self._connections[server_id]

    def get_server(self, server_id: str) -> MCPServerConnection | None:
        """Get a server connection."""
        return self._connections.get(server_id)

    def list_servers(self) -> list[str]:
        """List all server IDs."""
        return list(self._connections.keys())

    def get_all_status(self) -> dict[str, McpServerStatus]:
        """Get status of all servers."""
        return {
            sid: McpServerStatus(
                server_id=sid,
                connected=conn.is_connected,
                tools=conn.tools,
            )
            for sid, conn in self._connections.items()
        }
