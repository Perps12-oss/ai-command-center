"""CapabilityRegistry — Workspace OS syscall table (metadata only)."""

from __future__ import annotations

from ai_command_center.capabilities.catalog_v1 import build_v1_catalog
from ai_command_center.capabilities.definition import CapabilityDefinition


class CapabilityRegistry:
    """Owns CapabilityDefinitions. No execution logic."""

    def __init__(
        self,
        definitions: tuple[CapabilityDefinition, ...] | None = None,
    ) -> None:
        catalog = definitions if definitions is not None else build_v1_catalog()
        self._by_id: dict[str, CapabilityDefinition] = {c.id: c for c in catalog}

    def register(self, definition: CapabilityDefinition) -> None:
        self._by_id[definition.id] = definition

    def get(self, capability_id: str) -> CapabilityDefinition | None:
        return self._by_id.get(capability_id)

    def list_all(self) -> list[CapabilityDefinition]:
        return list(self._by_id.values())

    def list_planner_visible(self) -> list[CapabilityDefinition]:
        return [c for c in self._by_id.values() if c.planner_visible]

    def list_by_domain(self, domain: str) -> list[CapabilityDefinition]:
        return [c for c in self._by_id.values() if c.domain == domain]

    def to_prompt_specs(self, *, visible_only: bool = True) -> list[dict[str, object]]:
        caps = self.list_planner_visible() if visible_only else self.list_all()
        return [c.to_prompt_spec() for c in caps]
