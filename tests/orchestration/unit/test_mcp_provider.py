"""Layer 1 — provider registry and MCP adapter unit tests."""

from __future__ import annotations

from ai_command_center.core.permission.permission import PermissionContext
from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.mcp_adapter import McpAdapterProvider, McpProvider
from ai_command_center.orchestration.providers.mcp_client import McpServerConfig
from ai_command_center.orchestration.providers.provider_registry import OrchestrationProviderRegistry


def test_provider_registry_lists_builtin_providers() -> None:
    registry = OrchestrationProviderRegistry()
    assert "system_facts" in registry.list_providers()
    assert "application" in registry.list_providers()
    assert "calendar" in registry.list_providers()
    assert "mcp" in registry.list_providers()


def test_mcp_provider_unconfigured_is_unhealthy() -> None:
    provider = McpAdapterProvider()
    healthy, detail = provider.health()
    assert healthy is False
    assert "not configured" in detail.lower()


def test_provider_health_checks() -> None:
    registry = OrchestrationProviderRegistry()
    health = registry.health_checks()
    assert health["system_facts"][0] is True
    assert health["mcp"][0] is False


def test_mcp_provider_denies_without_permission() -> None:
    servers = {"local": McpServerConfig(server_id="local", command="echo")}
    provider = McpProvider(servers=servers)
    result = provider.execute(
        OrchestrationIntent.SYSTEM_TIME_QUERY,
        request_id="req-mcp",
        query="ping",
        args={},
    )
    assert result.success is False
    assert "permission denied" in (result.error or "").lower()


def test_mcp_provider_calls_tool_when_permitted() -> None:
    servers = {"local": McpServerConfig(server_id="local", command="echo")}

    def allow(_perm: str, _ctx: PermissionContext) -> bool:
        return True

    provider = McpProvider(servers=servers, permission_check=allow)
    result = provider.execute(
        OrchestrationIntent.SYSTEM_TIME_QUERY,
        request_id="req-mcp",
        query="ping",
        args={"server_id": "local", "tool": "ping"},
    )
    assert result.success is True
    assert result.facts.get("server_id") == "local"
    assert result.facts.get("tool") == "ping"
