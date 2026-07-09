"""Unified planner-facing capability catalog — metadata only, no handlers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ai_command_center.core.ai.capability_registry_service import (
    AICapabilityRegistryService,
)
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CAPABILITY_CATALOG_REQUEST,
    CAPABILITY_CATALOG_RESULT,
    CAPABILITY_LIFECYCLE_SNAPSHOT,
    EXTERNAL_CAPABILITY_CATALOG_UPDATED,
    EXTERNAL_CAPABILITY_REGISTERED,
    TOOL_REGISTERED,
)
from ai_command_center.domain.capability_lifecycle import CapabilityRecord
from ai_command_center.domain.capability_prompt_spec import CapabilityPromptSpec
from ai_command_center.domain.external_capability_manifest import ExternalCapabilityManifest
from ai_command_center.domain.execution_plan import RiskTier, capability_risk_for
from ai_command_center.services.base import BaseService
from ai_command_center.tools.tool_registry import ToolRegistry

_CALLABLE_LIFECYCLE = frozenset({"callable", "trusted", "exposed"})


def _tool_risk_metadata(tool_name: str) -> tuple[str, bool]:
    """Return (risk, requires_approval) for a registered tool."""
    tier = capability_risk_for(tool_name)
    risk = tier.value
    requires_approval = tier != RiskTier.LOW
    return risk, requires_approval


class CapabilityPromptCatalogService(BaseService):
    """Aggregates tool, AI, and runtime capability metadata for planners."""

    name = "capability_prompt_catalog"

    def __init__(
        self,
        bus,
        *,
        tool_registry: ToolRegistry,
        ai_capability_registry: AICapabilityRegistryService | None = None,
    ) -> None:
        super().__init__(bus)
        self._tool_registry = tool_registry
        self._ai_registry = ai_capability_registry
        self._lifecycle_records: dict[str, CapabilityRecord] = {}
        self._external_manifests: dict[str, ExternalCapabilityManifest] = {}
        self._unsubscribers: list[Callable[[], None]] = []

    def get_available_prompt_specs(self, entity_types: list[str]) -> list[dict[str, Any]]:
        """Return planner-facing specs; handlers are never included."""
        specs: list[CapabilityPromptSpec] = []
        seen: set[str] = set()

        for tool_name in self._tool_registry.list_tools():
            if tool_name in seen:
                continue
            described = self._tool_registry.describe_tool(tool_name)
            if described is None:
                continue
            risk, requires_approval = _tool_risk_metadata(tool_name)
            specs.append(
                CapabilityPromptSpec(
                    name=tool_name,
                    description=str(described.get("description", tool_name)),
                    risk=risk,
                    requires_approval=requires_approval,
                    parameters={"type": "object", "properties": {}},
                    source="tool",
                )
            )
            seen.add(tool_name)

        if self._ai_registry is not None:
            for entity_type in entity_types:
                for capability in self._ai_registry.get_capabilities(entity_type):
                    dedupe_key = f"ai:{capability.capability_type}"
                    if dedupe_key in seen:
                        continue
                    requires = bool(capability.required_permissions)
                    specs.append(
                        CapabilityPromptSpec(
                            name=capability.capability_type,
                            description=(
                                f"AI {capability.capability_type} "
                                f"for {entity_type} entities"
                            ),
                            risk="medium" if requires else "low",
                            requires_approval=requires,
                            parameters={
                                "type": "object",
                                "properties": {
                                    "entity_id": {"type": "string"},
                                },
                            },
                            source="ai_capability",
                        )
                    )
                    seen.add(dedupe_key)

        for record in self._lifecycle_records.values():
            if record.lifecycle_state.value not in _CALLABLE_LIFECYCLE:
                continue
            dedupe_key = f"runtime:{record.capability_id}"
            if dedupe_key in seen:
                continue
            healthy = record.health_status == "healthy"
            specs.append(
                CapabilityPromptSpec(
                    name=record.capability_id,
                    description=(
                        f"Runtime capability "
                        f"({record.capability_kind or record.source or 'provider'})"
                    ),
                    risk="low" if healthy else "medium",
                    requires_approval=not healthy,
                    parameters={"type": "object", "properties": {}},
                    source="runtime",
                )
            )
            seen.add(dedupe_key)

        for manifest in self._external_manifests.values():
            if not manifest.enabled:
                continue
            dedupe_key = f"external:{manifest.capability_id}"
            if dedupe_key in seen:
                continue
            spec_dict = manifest.to_prompt_spec()
            specs.append(
                CapabilityPromptSpec(
                    name=spec_dict["name"],
                    description=spec_dict["description"],
                    risk=spec_dict["risk"],
                    requires_approval=bool(spec_dict["requires_approval"]),
                    parameters=dict(spec_dict.get("parameters") or {}),
                    source="external",
                )
            )
            seen.add(dedupe_key)

        return [spec.to_dict() for spec in specs]

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(CAPABILITY_CATALOG_REQUEST, self._on_catalog_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(
                CAPABILITY_LIFECYCLE_SNAPSHOT, self._on_lifecycle_snapshot
            )
        )
        self._unsubscribers.append(
            self._bus.subscribe(TOOL_REGISTERED, self._on_tool_registered)
        )
        self._unsubscribers.append(
            self._bus.subscribe(
                EXTERNAL_CAPABILITY_REGISTERED, self._on_external_registered
            )
        )
        self._unsubscribers.append(
            self._bus.subscribe(
                EXTERNAL_CAPABILITY_CATALOG_UPDATED, self._on_external_catalog_updated
            )
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_tool_registered(self, _event: Event) -> None:
        # Registry is authoritative; event keeps catalog reactive for AppState consumers.
        return

    def _on_external_registered(self, event: Event) -> None:
        raw = event.payload.get("manifest")
        if isinstance(raw, dict):
            manifest = ExternalCapabilityManifest.from_dict(raw)
            if manifest.capability_id:
                self._external_manifests[manifest.capability_id] = manifest

    def _on_external_catalog_updated(self, event: Event) -> None:
        raw_manifests = event.payload.get("manifests") or []
        manifests: dict[str, ExternalCapabilityManifest] = {}
        for item in raw_manifests:
            if not isinstance(item, dict):
                continue
            manifest = ExternalCapabilityManifest.from_dict(item)
            if manifest.capability_id:
                manifests[manifest.capability_id] = manifest
        self._external_manifests = manifests

    def _on_lifecycle_snapshot(self, event: Event) -> None:
        raw_records = event.payload.get("capability_lifecycle") or []
        records: dict[str, CapabilityRecord] = {}
        for item in raw_records:
            if not isinstance(item, dict):
                continue
            record = CapabilityRecord.from_dict(item)
            if record.capability_id:
                records[record.capability_id] = record
        self._lifecycle_records = records

    def _on_catalog_request(self, event: Event) -> None:
        entity_types_raw = event.payload.get("entity_types") or []
        entity_types = [str(item) for item in entity_types_raw if str(item).strip()]
        specs = self.get_available_prompt_specs(entity_types)
        self._bus.publish(
            CAPABILITY_CATALOG_RESULT,
            {
                "request_id": event.payload.get("request_id", ""),
                "entity_types": entity_types,
                "specs": specs,
            },
            source=self.name,
        )
