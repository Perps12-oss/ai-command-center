"""MCP server settings helpers for orchestration provider."""

from __future__ import annotations

from ai_command_center.orchestration.providers.mcp_client import McpServerConfig


def parse_mcp_servers(raw: object) -> dict[str, McpServerConfig]:
    """Parse settings payload into MCP server configs (manifest stub)."""
    if not raw:
        return {}
    if isinstance(raw, dict):
        servers: dict[str, McpServerConfig] = {}
        for server_id, entry in raw.items():
            if isinstance(entry, dict):
                command = str(entry.get("command", "")).strip()
                args = tuple(str(a) for a in (entry.get("args") or []) if a)
                env = {str(k): str(v) for k, v in dict(entry.get("env") or {}).items()}
                servers[str(server_id)] = McpServerConfig(
                    server_id=str(server_id),
                    command=command,
                    args=args,
                    env=env,
                )
        return servers
    if isinstance(raw, str) and raw.strip():
        server_id = raw.strip()
        return {server_id: McpServerConfig(server_id=server_id)}
    return {}
