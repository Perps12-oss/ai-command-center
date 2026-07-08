"""MCP provider — first-class orchestration provider with permission gate."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ai_command_center.core.permission.permission import Permission, PermissionContext
from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult
from ai_command_center.orchestration.providers.mcp_client import (
    McpClient,
    McpServerConfig,
    StubMcpClient,
)

PermissionCheckFn = Callable[[str, PermissionContext], bool]


class McpProvider:
    """ACC Host → Provider Interface → MCP tools/call."""

    provider_id = "mcp"

    def __init__(
        self,
        *,
        servers: dict[str, McpServerConfig] | None = None,
        client: McpClient | None = None,
        permission_check: PermissionCheckFn | None = None,
    ) -> None:
        self._servers = servers or {}
        self._client = client or StubMcpClient(self._servers)
        self._permission_check = permission_check

    def health(self) -> tuple[bool, str]:
        if not self._servers:
            return False, "mcp servers not configured"
        return True, f"{len(self._servers)} server(s) configured"

    def execute(
        self,
        intent: OrchestrationIntent,
        *,
        request_id: str,
        query: str,
        args: dict[str, str],
    ) -> ProviderExecutionResult:
        if intent is OrchestrationIntent.UNHANDLED:
            return ProviderExecutionResult(
                success=False,
                error=f"unsupported intent: {intent.value}",
            )

        if not self._servers:
            return ProviderExecutionResult(
                success=False,
                error="MCP provider not configured — add mcp_servers in settings",
            )

        if not self._check_permission():
            return ProviderExecutionResult(
                success=False,
                error="permission denied for MCP tool call",
            )

        server_id = str(args.get("server_id", "")).strip() or next(iter(self._servers))
        tool_name = str(args.get("tool", "ping")).strip() or "ping"
        tool_args = _parse_tool_args(args.get("tool_args", ""))

        result = self._client.call_tool(server_id, tool_name, tool_args)
        if not result.success:
            return ProviderExecutionResult(
                success=False,
                error=result.error or "MCP tool call failed",
                facts={"server_id": server_id, "tool": tool_name},
            )

        return ProviderExecutionResult(
            success=True,
            response_text=f"MCP tool {tool_name} completed on {server_id}.",
            facts={
                "server_id": server_id,
                "tool": tool_name,
                "mcp_output": result.output,
            },
        )

    def _check_permission(self) -> bool:
        if self._permission_check is None:
            return False
        context = PermissionContext(
            entity_id=None,
            entity_type=None,
            action_id=None,
            actor_type="user",
            actor_id=None,
        )
        return self._permission_check(Permission.LAUNCH_TOOL.value, context)


def _parse_tool_args(raw: str) -> dict[str, Any]:
    text = str(raw).strip()
    if not text:
        return {}
    return {"query": text}


# Backward-compatible alias for registry/tests written during PR3 skeleton.
McpAdapterProvider = McpProvider
