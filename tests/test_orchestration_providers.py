"""Tests for orchestration provider registry and MCP skeleton."""

from __future__ import annotations

from ai_command_center.orchestration.providers.mcp_adapter import McpAdapterProvider
from ai_command_center.orchestration.providers.provider_registry import OrchestrationProviderRegistry


def test_provider_registry_lists_builtin_providers() -> None:
    registry = OrchestrationProviderRegistry()
    assert "system_facts" in registry.list_providers()
    assert "application" in registry.list_providers()
    assert "calendar" in registry.list_providers()
    assert "mcp" in registry.list_providers()


def test_mcp_adapter_skeleton_unhealthy() -> None:
    provider = McpAdapterProvider()
    healthy, detail = provider.health()
    assert healthy is False
    assert "skeleton" in detail.lower() or "not configured" in detail.lower()


def test_provider_health_checks() -> None:
    registry = OrchestrationProviderRegistry()
    health = registry.health_checks()
    assert health["system_facts"][0] is True
    assert health["mcp"][0] is False
