"""Registry of orchestration providers."""

from __future__ import annotations

from ai_command_center.orchestration.providers.application_provider import ApplicationProvider
from ai_command_center.orchestration.providers.calendar_provider import CalendarProvider
from ai_command_center.orchestration.providers.mcp_adapter import McpAdapterProvider, McpProvider
from ai_command_center.orchestration.providers.provider_protocol import OrchestrationProvider
from ai_command_center.orchestration.providers.system_facts_provider import SystemFactsProvider


class OrchestrationProviderRegistry:
    """Resolves orchestration providers by id."""

    def __init__(
        self,
        *,
        system_facts: SystemFactsProvider | None = None,
        application: ApplicationProvider | None = None,
        calendar: CalendarProvider | None = None,
        mcp: McpAdapterProvider | McpProvider | None = None,
    ) -> None:
        self._providers: dict[str, OrchestrationProvider] = {}
        for provider in (
            system_facts or SystemFactsProvider(),
            application or ApplicationProvider(),
            calendar or CalendarProvider(),
            mcp or McpAdapterProvider(),
        ):
            self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> OrchestrationProvider | None:
        return self._providers.get(provider_id)

    def list_providers(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def health_checks(self) -> dict[str, tuple[bool, str]]:
        return {
            provider_id: provider.health()
            for provider_id, provider in self._providers.items()
        }
