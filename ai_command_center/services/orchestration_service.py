"""Truth-bound orchestration service — EventBus integration."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.intents import INTENT_CHAT, INTENT_SHELL
from ai_command_center.core.events.topics import (
    CAPABILITY_PROVIDERS_READY,
    CHAT_COMPLETE,
    CHAT_STARTED,
    COMMAND_ROUTED,
    ORCHESTRATION_INTENT_CLASSIFIED,
    ORCHESTRATION_PROVIDER_HEALTH,
    ORCHESTRATION_PROVIDER_SELECTED,
    ORCHESTRATION_RECEIPT,
    ORCHESTRATION_ROUTING_COMPLETED,
    ORCHESTRATION_RUN_SNAPSHOT,
    ORCHESTRATION_TRUTH_VALIDATED,
    SESSION_UPDATE_REQUEST,
    TELEMETRY_EVENT,
)
from ai_command_center.orchestration.execution.executor import OrchestrationExecutor
from ai_command_center.orchestration.execution.response_composer import ResponseComposer
from ai_command_center.orchestration.intents.classifier import RuleBasedIntentClassifier
from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.orchestration_registry import mark_orchestration_request
from ai_command_center.orchestration.policies.fallback_policy import OrchestrationFallbackPolicy
from ai_command_center.orchestration.providers.provider_registry import OrchestrationProviderRegistry
from ai_command_center.orchestration.routing.intent_router import IntentRouter
from ai_command_center.orchestration.state.orchestration_snapshot import OrchestrationRunSnapshot
from ai_command_center.orchestration.verification.truth_boundary import TruthBoundary
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)

_SCOPE_KEYS: tuple[str, ...] = (
    "workspace_id",
    "selected_entity_id",
    "selected_entity_type",
    "selected_entity_title",
)


def _routing_scope(payload: dict[str, object], args: dict[str, object]) -> dict[str, str]:
    """Workspace scope from command.routed for classify and provider execution."""
    scope: dict[str, str] = {}
    workspace_id = str(payload.get("workspace_id") or args.get("workspace_id", "")).strip()
    if workspace_id:
        scope["workspace_id"] = workspace_id
    for key in _SCOPE_KEYS[1:]:
        value = str(payload.get(key) or args.get(key, "")).strip()
        if value:
            scope[key] = value
    return scope


def _observability_scope(payload: dict[str, object]) -> dict[str, str]:
    """Pass workspace/entity scope through orchestration events for tracing."""
    scope: dict[str, str] = {}
    workspace_id = str(payload.get("workspace_id", "")).strip()
    if workspace_id:
        scope["workspace_id"] = workspace_id
    entity_id = str(payload.get("entity_id", "")).strip()
    if not entity_id:
        entity_id = str(payload.get("selected_entity_id", "")).strip()
    if entity_id:
        scope["entity_id"] = entity_id
    return scope


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
        # Refresh orchestration provider health when runtime providers reload, so the
        # Runtime Inspector dashboard doesn't go stale after plugin changes.
        self._unsubscribers.append(
            self._bus.subscribe(CAPABILITY_PROVIDERS_READY, self._on_capability_providers_ready)
        )
        self._publish_provider_health()

    def _on_capability_providers_ready(self, _event: Event) -> None:
        self._publish_provider_health()

    def _publish_provider_health(self) -> None:
        for provider_id, (healthy, detail) in self._registry.health_checks().items():
            self._bus.publish(
                ORCHESTRATION_PROVIDER_HEALTH,
                {
                    "provider_id": provider_id,
                    "healthy": healthy,
                    "detail": detail,
                    "display_name": provider_id,
                },
                source=self.name,
            )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def _on_command_routed(self, event: Event) -> None:
        if event.source != "command_router":
            return

        routed_intent = str(event.payload.get("intent", "")).strip()
        args = event.payload.get("args") or {}
        request_id = str(event.payload.get("request_id", "")).strip()
        scope = _routing_scope(dict(event.payload), dict(args))
        for key, value in _observability_scope(event.payload).items():
            scope.setdefault(key, value)

        # Shell commands: route directly to ShellProvider via orchestration
        if routed_intent == INTENT_SHELL:
            command = str(args.get("command", "")).strip()
            if not command:
                return
            self._orchestrate_shell(request_id, command, scope)
            return

        # Chat commands: classify and route
        if routed_intent != INTENT_CHAT:
            return

        query = str(args.get("prompt", "")).strip()
        if not query:
            return

        intent, intent_args = self._classifier.classify(query)
        merged_args = {**intent_args, **scope}
        classified_payload: dict[str, object] = {
            "request_id": request_id,
            "query": query,
            "intent": intent.value,
            "args": merged_args,
        }
        classified_payload.update(scope)
        self._bus.publish(
            ORCHESTRATION_INTENT_CLASSIFIED,
            classified_payload,
            source=self.name,
        )

        if OrchestrationFallbackPolicy.should_defer_to_llm(intent):
            return

        provider_id = self._intent_router.resolve_provider(intent)
        self._bus.publish(
            ORCHESTRATION_ROUTING_COMPLETED,
            {
                "request_id": request_id,
                "intent": intent.value,
                "provider_id": provider_id,
                "routed": bool(provider_id),
                **scope,
            },
            source=self.name,
        )
        if not provider_id:
            return

        self._bus.publish(
            ORCHESTRATION_PROVIDER_SELECTED,
            {
                "request_id": request_id,
                "intent": intent.value,
                "provider_id": provider_id,
                **scope,
            },
            source=self.name,
        )

        self._execute_and_respond(
            intent=intent,
            provider_id=provider_id,
            request_id=request_id,
            query=query,
            args=merged_args,
        )

    def _orchestrate_shell(
        self,
        request_id: str,
        command: str,
        scope: dict[str, str],
    ) -> None:
        """Execute shell command via ShellProvider with receipts and truth validation.

        Shell commands REQUIRE a workspace_id for execution. Without a workspace,
        commands are rejected at the truth boundary.
        """
        # Workspace enforcement: shell commands must have workspace_id
        workspace_id = scope.get("workspace_id", "").strip()
        if not workspace_id:
            # Shell without workspace: emit rejection at truth boundary
            self._bus.publish(
                ORCHESTRATION_TRUTH_VALIDATED,
                {
                    "request_id": request_id,
                    "valid": False,
                    "detail": "shell command requires active workspace",
                    "response_source": "orchestration_rejected",
                },
                source=self.name,
            )
            self._bus.publish(
                CHAT_COMPLETE,
                {
                    "request_id": request_id,
                    "text": "Shell commands require an active workspace. Please select a workspace first.",
                    "response_source": "orchestration_rejected",
                    "truth_validated": False,
                    "orchestration": {
                        "intent": "execute_shell",
                        "provider_id": "shell",
                        "receipt_id": "",
                        "truth_detail": "shell command requires active workspace",
                    },
                },
                source=self.name,
            )
            return

        intent = OrchestrationIntent.EXECUTE_SHELL
        provider_id = "shell"
        args = {"command": command, **scope}

        self._bus.publish(
            ORCHESTRATION_INTENT_CLASSIFIED,
            {
                "request_id": request_id,
                "query": command,
                "intent": intent.value,
                "args": args,
                **scope,
            },
            source=self.name,
        )

        self._bus.publish(
            ORCHESTRATION_ROUTING_COMPLETED,
            {
                "request_id": request_id,
                "intent": intent.value,
                "provider_id": provider_id,
                "routed": True,
                **scope,
            },
            source=self.name,
        )

        self._bus.publish(
            ORCHESTRATION_PROVIDER_SELECTED,
            {
                "request_id": request_id,
                "intent": intent.value,
                "provider_id": provider_id,
                **scope,
            },
            source=self.name,
        )

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
            query=command,
            args=args,
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
            query=command,
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
            trace_id=uuid.uuid4().hex,
            span_id=uuid.uuid4().hex[:16],
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
                "content": command,
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

    def _execute_and_respond(
        self,
        intent: OrchestrationIntent,
        provider_id: str,
        request_id: str,
        query: str,
        args: dict[str, str],
    ) -> None:
        """Execute provider and emit all required events."""
        run = self._executor.run(
            intent,
            provider_id,
            request_id=request_id,
            query=query,
            args=args,
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
            trace_id=uuid.uuid4().hex,
            span_id=uuid.uuid4().hex[:16],
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
