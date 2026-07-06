"""Truth-bound orchestration service — EventBus integration."""

from __future__ import annotations

import logging
from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.intents import INTENT_CHAT
from ai_command_center.core.events.topics import (
    CHAT_COMPLETE,
    CHAT_STARTED,
    COMMAND_ROUTED,
    ORCHESTRATION_INTENT_CLASSIFIED,
    ORCHESTRATION_RECEIPT,
    ORCHESTRATION_RUN_SNAPSHOT,
    ORCHESTRATION_TRUTH_VALIDATED,
    SESSION_UPDATE_REQUEST,
    TELEMETRY_EVENT,
)
from ai_command_center.orchestration.execution.executor import OrchestrationExecutor
from ai_command_center.orchestration.execution.response_composer import ResponseComposer
from ai_command_center.orchestration.intents.classifier import RuleBasedIntentClassifier
from ai_command_center.orchestration.orchestration_registry import mark_orchestration_request
from ai_command_center.orchestration.policies.fallback_policy import OrchestrationFallbackPolicy
from ai_command_center.orchestration.providers.provider_registry import OrchestrationProviderRegistry
from ai_command_center.orchestration.routing.intent_router import IntentRouter
from ai_command_center.orchestration.state.orchestration_snapshot import OrchestrationRunSnapshot
from ai_command_center.orchestration.verification.truth_boundary import TruthBoundary
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)


class OrchestrationService(BaseService):
    """Classifies truth-bound intents and completes chat without LLM when matched."""

    name = "orchestration"

    def __init__(
        self,
        bus,
        *,
        provider_registry: OrchestrationProviderRegistry | None = None,
        classifier: RuleBasedIntentClassifier | None = None,
        intent_router: IntentRouter | None = None,
        executor: OrchestrationExecutor | None = None,
        truth_boundary: TruthBoundary | None = None,
        response_composer: ResponseComposer | None = None,
    ) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        registry = provider_registry or OrchestrationProviderRegistry()
        self._classifier = classifier or RuleBasedIntentClassifier()
        self._intent_router = intent_router or IntentRouter()
        self._executor = executor or OrchestrationExecutor(registry)
        self._truth_boundary = truth_boundary or TruthBoundary()
        self._response_composer = response_composer or ResponseComposer()
        self._registry = registry

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(COMMAND_ROUTED, self._on_command_routed)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_command_routed(self, event: Event) -> None:
        if event.source != "command_router":
            return
        if event.payload.get("intent") != INTENT_CHAT:
            return

        args = event.payload.get("args") or {}
        query = str(args.get("prompt", "")).strip()
        if not query:
            return

        request_id = str(event.payload.get("request_id", "")).strip()
        intent, intent_args = self._classifier.classify(query)
        self._bus.publish(
            ORCHESTRATION_INTENT_CLASSIFIED,
            {
                "request_id": request_id,
                "query": query,
                "intent": intent.value,
                "args": intent_args,
            },
            source=self.name,
        )

        if OrchestrationFallbackPolicy.should_defer_to_llm(intent):
            return

        provider_id = self._intent_router.resolve_provider(intent)
        if not provider_id:
            return

        mark_orchestration_request(request_id)
        _logger.info(
            "orchestration.dispatch request_id=%s intent=%s provider=%s",
            request_id,
            intent.value,
            provider_id,
        )

        run = self._executor.run(
            intent,
            provider_id,
            request_id=request_id,
            query=query,
            args=intent_args,
        )
        self._bus.publish(
            ORCHESTRATION_RECEIPT,
            run.receipt.to_dict(),
            source=self.name,
        )

        validation = self._truth_boundary.validate(intent, run.result, run.receipt)
        self._bus.publish(
            ORCHESTRATION_TRUTH_VALIDATED,
            {
                "request_id": request_id,
                "valid": validation.valid,
                "detail": validation.detail,
                "response_source": validation.response_source,
            },
            source=self.name,
        )

        composed = self._response_composer.compose(
            intent=intent,
            provider_id=provider_id,
            validation=validation,
            receipt=run.receipt,
        )
        snapshot = OrchestrationRunSnapshot(
            request_id=request_id,
            query=query,
            intent=intent.value,
            provider_id=provider_id,
            execution_success=run.result.success,
            execution_facts=dict(run.result.facts),
            execution_error=run.result.error,
            truth_valid=validation.valid,
            truth_detail=validation.detail,
            response_source=validation.response_source,
            response_text=composed.text,
            receipt_id=run.receipt.receipt_id,
        )
        self._bus.publish(
            ORCHESTRATION_RUN_SNAPSHOT,
            snapshot.to_dict(),
            source=self.name,
        )

        self._bus.publish(
            CHAT_STARTED,
            {"request_id": request_id, "orchestration": True},
            source=self.name,
        )
        self._bus.publish(
            SESSION_UPDATE_REQUEST,
            {
                "request_id": request_id,
                "role": "user",
                "content": query,
            },
            source=self.name,
        )
        complete_payload = self._response_composer.to_chat_complete_payload(
            composed,
            request_id=request_id,
        )
        self._bus.publish(CHAT_COMPLETE, complete_payload, source=self.name)
        self._bus.publish(
            SESSION_UPDATE_REQUEST,
            {
                "request_id": request_id,
                "role": "assistant",
                "content": composed.text,
            },
            source=self.name,
        )
        self._bus.publish(
            TELEMETRY_EVENT,
            {
                "name": "orchestration.complete",
                "request_id": request_id,
                "intent": intent.value,
                "provider_id": provider_id,
                "truth_valid": validation.valid,
            },
            source=self.name,
        )
