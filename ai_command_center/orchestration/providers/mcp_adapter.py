"""MCP adapter skeleton — ACC Host → Provider Interface → MCP (PR3)."""

from __future__ import annotations

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult


class McpAdapterProvider:
    """Skeleton MCP bridge; no real MCP providers wired in PR3."""

    provider_id = "mcp"

    def health(self) -> tuple[bool, str]:
        return False, "mcp adapter not configured"

    def execute(
        self,
        intent: OrchestrationIntent,
        *,
        request_id: str,
        query: str,
        args: dict[str, str],
    ) -> ProviderExecutionResult:
        return ProviderExecutionResult(
            success=False,
            error="MCP adapter skeleton — no providers registered",
        )
