"""CapabilityPromptCatalogService — Phase B facade tests."""

from __future__ import annotations

from ai_command_center.core.ai.capability import CAPABILITY_SUMMARIZE
from ai_command_center.core.ai.capability_registry_service import (
    AICapabilityRegistryService,
)
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CAPABILITY_CATALOG_REQUEST,
    CAPABILITY_CATALOG_RESULT,
    CAPABILITY_LIFECYCLE_SNAPSHOT,
)
from ai_command_center.core.tools import ToolSpec
from ai_command_center.domain.capability_lifecycle import (
    CapabilityLifecycleState,
    CapabilityRecord,
)
from ai_command_center.services.capability_prompt_catalog_service import (
    CapabilityPromptCatalogService,
)
from ai_command_center.tools.tool_registry import ToolRegistry


def _noop_handler(_entity_id, _params):
    return "ok"


def _noop_tool(_args):
    from ai_command_center.core.tools import ToolResult

    return ToolResult(success=True, output="ok")


def test_catalog_specs_exclude_handlers() -> None:
    bus = EventBus()
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="create_note", description="Creates a note entity", handler=_noop_tool)
    )

    permission = type("Perm", (), {"check": lambda self, perm, ctx: True})()
    ai_registry = AICapabilityRegistryService(permission)
    ai_registry.register_capability(
        entity_type="card",
        capability_type=CAPABILITY_SUMMARIZE,
        handler=_noop_handler,
        required_permissions=["entity.read"],
    )

    service = CapabilityPromptCatalogService(
        bus,
        tool_registry=registry,
        ai_capability_registry=ai_registry,
    )
    service.start()

    bus.publish(
        CAPABILITY_LIFECYCLE_SNAPSHOT,
        {
            "capability_lifecycle": [
                CapabilityRecord(
                    capability_id="planning.native",
                    provider_id="native",
                    lifecycle_state=CapabilityLifecycleState.CALLABLE,
                    capability_kind="planning",
                    source="runtime",
                    health_status="healthy",
                ).to_dict()
            ]
        },
        source="test",
    )

    results: list[dict] = []
    bus.subscribe(CAPABILITY_CATALOG_RESULT, lambda e: results.append(dict(e.payload)))

    bus.publish(
        CAPABILITY_CATALOG_REQUEST,
        {"request_id": "req-1", "entity_types": ["card"]},
        source="test",
    )

    assert results
    payload = results[0]
    assert payload["request_id"] == "req-1"
    specs = payload["specs"]
    assert specs

    names = {spec["name"] for spec in specs}
    assert "create_note" in names
    assert CAPABILITY_SUMMARIZE in names
    assert "planning.native" in names

    for spec in specs:
        assert "handler" not in spec
        assert set(spec.keys()) == {
            "name",
            "description",
            "risk",
            "requires_approval",
            "parameters",
        }

    tool_spec = next(s for s in specs if s["name"] == "create_note")
    assert tool_spec["requires_approval"] is False
    assert tool_spec["risk"] == "low"

    ai_spec = next(s for s in specs if s["name"] == CAPABILITY_SUMMARIZE)
    assert ai_spec["requires_approval"] is True


def test_get_available_prompt_specs_direct() -> None:
    bus = EventBus()
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="search_files", description="Search workspace files", handler=_noop_tool)
    )
    service = CapabilityPromptCatalogService(bus, tool_registry=registry)
    service.start()

    specs = service.get_available_prompt_specs([])
    assert len(specs) == 1
    assert specs[0]["name"] == "search_files"
    assert "handler" not in specs[0]
