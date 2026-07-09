"""ExternalCapabilityBridgeService — Phase E integration scaffold tests."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CAPABILITY_CATALOG_REQUEST,
    CAPABILITY_CATALOG_RESULT,
    EXTERNAL_CAPABILITY_CATALOG_UPDATED,
    EXTERNAL_CAPABILITY_REGISTER,
    EXTERNAL_CAPABILITY_REGISTERED,
    EXTERNAL_CAPABILITY_UNREGISTER,
)
from ai_command_center.domain.external_capability_manifest import ExternalCapabilityManifest
from ai_command_center.services.capability_prompt_catalog_service import (
    CapabilityPromptCatalogService,
)
from ai_command_center.services.external_capability_bridge_service import (
    ExternalCapabilityBridgeService,
)
from ai_command_center.tools.tool_registry import ToolRegistry


def test_register_publishes_registered_and_catalog_updated() -> None:
    bus = EventBus()
    bridge = ExternalCapabilityBridgeService(bus)
    bridge.start()

    registered: list[dict] = []
    catalog_updates: list[dict] = []
    bus.subscribe(
        EXTERNAL_CAPABILITY_REGISTERED, lambda e: registered.append(dict(e.payload))
    )
    bus.subscribe(
        EXTERNAL_CAPABILITY_CATALOG_UPDATED,
        lambda e: catalog_updates.append(dict(e.payload)),
    )

    manifest = ExternalCapabilityManifest(
        capability_id="mcp.filesystem.read",
        name="Read file",
        description="Read a file via MCP filesystem server",
        provider_id="mcp-filesystem",
        risk="medium",
        kind="mcp",
    )
    bus.publish(
        EXTERNAL_CAPABILITY_REGISTER,
        {"manifest": manifest.to_dict()},
        source="test",
    )

    assert registered
    assert registered[0]["manifest"]["capability_id"] == "mcp.filesystem.read"
    assert catalog_updates
    assert catalog_updates[-1]["count"] == 1
    assert bridge.get_manifest("mcp.filesystem.read") is not None


def test_unregister_removes_from_bridge_cache() -> None:
    bus = EventBus()
    bridge = ExternalCapabilityBridgeService(bus)
    bridge.start()

    bus.publish(
        EXTERNAL_CAPABILITY_REGISTER,
        {
            "manifest": ExternalCapabilityManifest(
                capability_id="mcp.temp",
                name="Temp",
                description="temp",
                provider_id="mcp",
            ).to_dict()
        },
        source="test",
    )
    assert bridge.list_manifests()

    bus.publish(
        EXTERNAL_CAPABILITY_UNREGISTER,
        {"capability_id": "mcp.temp"},
        source="test",
    )
    assert bridge.list_manifests() == []


def test_catalog_includes_external_manifests_from_bridge() -> None:
    bus = EventBus()
    registry = ToolRegistry()
    catalog = CapabilityPromptCatalogService(bus, tool_registry=registry)
    bridge = ExternalCapabilityBridgeService(bus)
    catalog.start()
    bridge.start()

    bus.publish(
        EXTERNAL_CAPABILITY_REGISTER,
        {
            "manifest": ExternalCapabilityManifest(
                capability_id="mcp.calendar.list_events",
                name="List calendar events",
                description="List events from connected calendar MCP server",
                provider_id="mcp-calendar",
                risk="low",
                kind="mcp",
            ).to_dict()
        },
        source="test",
    )

    results: list[dict] = []
    bus.subscribe(CAPABILITY_CATALOG_RESULT, lambda e: results.append(dict(e.payload)))

    bus.publish(
        CAPABILITY_CATALOG_REQUEST,
        {"request_id": "cat-1", "entity_types": []},
        source="test",
    )

    assert results
    specs = results[0]["specs"]
    names = {spec["name"] for spec in specs}
    assert "mcp.calendar.list_events" in names
    ext = next(s for s in specs if s["name"] == "mcp.calendar.list_events")
    assert ext["risk"] == "low"
    assert ext["requires_approval"] is False


def test_register_accepts_flat_payload() -> None:
    bus = EventBus()
    bridge = ExternalCapabilityBridgeService(bus)
    bridge.start()

    bus.publish(
        EXTERNAL_CAPABILITY_REGISTER,
        {
            "capability_id": "external.email.send",
            "name": "Send email",
            "description": "Send email via external provider",
            "provider_id": "email-stub",
            "risk": "high",
            "kind": "email",
        },
        source="test",
    )

    manifest = bridge.get_manifest("external.email.send")
    assert manifest is not None
    assert manifest.kind == "email"
    assert manifest.risk == "high"
