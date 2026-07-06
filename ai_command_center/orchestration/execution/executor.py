"""Runs orchestration providers and builds receipts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult
from ai_command_center.orchestration.providers.provider_registry import OrchestrationProviderRegistry
from ai_command_center.orchestration.receipts.execution_receipt import ExecutionReceipt


@dataclass(frozen=True, slots=True)
class OrchestrationRun:
    intent: OrchestrationIntent
    provider_id: str
    result: ProviderExecutionResult
    receipt: ExecutionReceipt


class OrchestrationExecutor:
    """Invokes a provider and always emits an execution receipt."""

    def __init__(self, registry: OrchestrationProviderRegistry) -> None:
        self._registry = registry

    def run(
        self,
        intent: OrchestrationIntent,
        provider_id: str,
        *,
        request_id: str,
        query: str,
        args: dict[str, str],
    ) -> OrchestrationRun:
        provider = self._registry.get(provider_id)
        if provider is None:
            result = ProviderExecutionResult(
                success=False,
                error=f"provider not registered: {provider_id}",
            )
        else:
            healthy, detail = provider.health()
            if not healthy and intent is not OrchestrationIntent.CALENDAR_QUERY:
                result = ProviderExecutionResult(success=False, error=detail or "provider unhealthy")
            else:
                result = provider.execute(
                    intent,
                    request_id=request_id,
                    query=query,
                    args=args,
                )

        receipt = ExecutionReceipt(
            receipt_id=uuid.uuid4().hex,
            request_id=request_id,
            intent=intent.value,
            provider_id=provider_id,
            success=result.success,
            facts=tuple(sorted(result.facts.items(), key=lambda item: item[0])),
            error=result.error,
        )
        return OrchestrationRun(
            intent=intent,
            provider_id=provider_id,
            result=result,
            receipt=receipt,
        )
