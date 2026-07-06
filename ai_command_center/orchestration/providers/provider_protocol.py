"""Orchestration provider protocol."""

from __future__ import annotations

from typing import Protocol

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult


class OrchestrationProvider(Protocol):
    provider_id: str

    def health(self) -> tuple[bool, str]: ...

    def execute(
        self,
        intent: OrchestrationIntent,
        *,
        request_id: str,
        query: str,
        args: dict[str, str],
    ) -> ProviderExecutionResult: ...
