"""Uniform receipt / truth / World-Model completion for every execution run.

Shell and application execution flow through
ExecutionAuthority → ExecutionOrchestrator → tools.
This service observes EXECUTION_RUN_COMPLETE / FAILED and emits the evidence
set required by the Single Execution-Authority Contract (C-4).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CAPABILITY_PROVIDERS_READY,
    CHAT_COMPLETE,
    CHAT_STARTED,
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    ORCHESTRATION_PROVIDER_HEALTH,
    ORCHESTRATION_RUN_SNAPSHOT,
    RUNTIME_ACTION_REQUEST,
    SESSION_UPDATE_REQUEST,
    TELEMETRY_EVENT,
)
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.orchestration_run_snapshot import (
    OrchestrationRunSnapshot,
    _dict_to_immutable,
)
from ai_command_center.domain.runtime_safety import SecurityTier
from ai_command_center.domain.world_model import MutationType
from ai_command_center.orchestration.providers.provider_registry import (
    OrchestrationProviderRegistry,
)
from ai_command_center.orchestration.receipts.boundary_emit import (
    RECEIPT_BUS_SOURCE,
    emit_execution_receipt,
)
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)


class OrchestrationService(BaseService):
    """Completion observer — receipts, truth validation, World Model, UI response."""

    name = "orchestration"

    def __init__(
        self,
        bus,
        *,
        provider_registry: OrchestrationProviderRegistry | None = None,
        **_deprecated: object,
    ) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._registry = provider_registry or OrchestrationProviderRegistry()

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_RUN_COMPLETE, self._on_execution_complete)
        )
        self._unsubscribers.append(
            self._bus.subscribe(EXECUTION_RUN_FAILED, self._on_execution_failed)
        )
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

    def _on_execution_complete(self, event: Event) -> None:
        self._emit_completion(event, success=True, error="")

    def _on_execution_failed(self, event: Event) -> None:
        self._emit_completion(
            event,
            success=False,
            error=str(event.payload.get("error") or "execution failed"),
        )

    def _emit_completion(
        self,
        event: Event,
        *,
        success: bool,
        error: str,
    ) -> None:
        payload = dict(event.payload)
        pre_emitted = bool(payload.get("receipt_already_emitted"))
        evidence: dict | None = None
        if pre_emitted and success:
            # EOS already published receipt+truth before COMPLETE (B-1 gate).
            evidence = {
                "request_id": str(payload.get("request_id") or payload.get("run_id") or ""),
                "receipt_id": str(payload.get("receipt_id") or ""),
                "run_id": str(payload.get("run_id") or ""),
                "goal": str(payload.get("goal") or ""),
                "primary_capability": str(payload.get("primary_capability") or ""),
                "facts": payload.get("execution_facts")
                if isinstance(payload.get("execution_facts"), dict)
                else {},
                "truth_valid": bool(payload.get("truth_valid")),
                "truth_detail": str(payload.get("truth_detail") or ""),
                "response_source": str(payload.get("response_source") or "orchestration"),
                "response_text": str(payload.get("response_text") or ""),
                "scope_fields": {},
            }
            workspace_context = (
                payload.get("workspace_context")
                if isinstance(payload.get("workspace_context"), dict)
                else {}
            )
            workspace_id = str(
                workspace_context.get("workspace_id") or payload.get("workspace_id") or ""
            ).strip()
            entity_id = str(workspace_context.get("entity_id") or "").strip()
            if workspace_id:
                evidence["scope_fields"]["workspace_id"] = workspace_id
            if entity_id:
                evidence["scope_fields"]["entity_id"] = entity_id
        else:
            evidence = emit_execution_receipt(
                self._bus,
                payload=payload,
                success=success,
                error=error,
                source=RECEIPT_BUS_SOURCE,
            )
            if evidence is None:
                _logger.error(
                    "orchestration.completion_receipt_failed success=%s",
                    success,
                )
                return

        request_id = str(evidence["request_id"])
        run_id = str(evidence.get("run_id") or "")
        goal = str(evidence.get("goal") or "")
        primary_capability = str(evidence.get("primary_capability") or "")
        facts = evidence.get("facts") if isinstance(evidence.get("facts"), dict) else {}
        truth_valid = bool(evidence.get("truth_valid"))
        truth_detail = str(evidence.get("truth_detail") or "")
        response_source = str(evidence.get("response_source") or "orchestration")
        response_text = str(evidence.get("response_text") or "")
        receipt_id = str(evidence.get("receipt_id") or "")
        scope_fields = (
            dict(evidence["scope_fields"])
            if isinstance(evidence.get("scope_fields"), dict)
            else {}
        )
        plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
        step_outputs = list(payload.get("step_outputs") or [])

        snapshot = OrchestrationRunSnapshot(
            request_id=request_id,
            query=goal,
            intent=primary_capability or "execution_run",
            provider_id="execution_orchestrator",
            execution_success=success,
            execution_facts=_dict_to_immutable(facts),
            execution_error=error or None,
            truth_valid=truth_valid,
            truth_detail=truth_detail,
            response_source=response_source,
            response_text=response_text,
            receipt_id=receipt_id,
            trace_id=uuid.uuid4().hex,
            span_id=uuid.uuid4().hex[:16],
        )
        self._bus.publish(
            ORCHESTRATION_RUN_SNAPSHOT,
            snapshot.to_dict(),
            source=self.name,
        )

        correlation = CorrelationContext.from_payload(payload).with_action(run_id or request_id)
        for node in _world_model_nodes_for_run(
            request_id=request_id,
            run_id=run_id,
            goal=goal,
            primary_capability=primary_capability,
            success=success,
            receipt_id=receipt_id,
            plan=plan if isinstance(plan, dict) else {},
            step_outputs=step_outputs,
        ):
            mutation_id = uuid.uuid4().hex
            self._bus.publish(
                RUNTIME_ACTION_REQUEST,
                {
                    "action_id": run_id or request_id,
                    "tier": SecurityTier.WRITE.value,
                    "auto_approve": True,
                    "summary": f"Record {node['type']} {node['id']}",
                    "mutation": {
                        "id": mutation_id,
                        "type": MutationType.CREATE_NODE.value,
                        "correlation": correlation.to_payload(),
                        "payload": {"node": node},
                    },
                    "correlation": correlation.to_payload(),
                    "output": {
                        "request_id": request_id,
                        "run_id": run_id,
                        "receipt_id": receipt_id,
                        "node_id": node["id"],
                        "node_type": node["type"],
                    },
                    **scope_fields,
                },
                source=self.name,
            )

        self._bus.publish(
            CHAT_STARTED,
            {
                "request_id": request_id,
                "orchestration": True,
                "execution_run": True,
                **scope_fields,
            },
            source=self.name,
        )
        if goal:
            self._bus.publish(
                SESSION_UPDATE_REQUEST,
                {
                    "request_id": request_id,
                    "role": "user",
                    "content": goal,
                    **scope_fields,
                },
                source=self.name,
            )
        self._bus.publish(
            CHAT_COMPLETE,
            {
                "request_id": request_id,
                "text": response_text,
                "response_source": response_source,
                "truth_validated": truth_valid,
                "orchestration": {
                    "intent": primary_capability or "execution_run",
                    "provider_id": "execution_orchestrator",
                    "receipt_id": receipt_id,
                    "truth_detail": truth_detail,
                    "run_id": run_id,
                },
                **scope_fields,
            },
            source=self.name,
        )
        self._bus.publish(
            SESSION_UPDATE_REQUEST,
            {
                "request_id": request_id,
                "role": "assistant",
                "content": response_text,
                **scope_fields,
            },
            source=self.name,
        )
        self._bus.publish(
            TELEMETRY_EVENT,
            {
                "name": "execution.complete",
                "request_id": request_id,
                "run_id": run_id,
                "capability": primary_capability,
                "truth_valid": truth_valid,
                "success": success,
                **scope_fields,
            },
            source=self.name,
        )
        _logger.info(
            "orchestration.completion_observed request_id=%s run_id=%s success=%s",
            request_id,
            run_id,
            success,
        )


def _world_model_nodes_for_run(
    *,
    request_id: str,
    run_id: str,
    goal: str,
    primary_capability: str,
    success: bool,
    receipt_id: str,
    plan: dict,
    step_outputs: list[object],
) -> list[dict]:
    """Build World Model nodes: always an execution_run, plus domain entities."""
    nodes: list[dict] = [
        {
            "id": f"execution_run:{run_id or request_id}",
            "type": "execution_run",
            "attributes": {
                "request_id": request_id,
                "run_id": run_id,
                "goal": goal,
                "capability": primary_capability,
                "success": success,
                "receipt_id": receipt_id,
            },
        }
    ]
    if not success:
        return nodes

    steps = list(plan.get("steps") or [])
    step0 = steps[0] if steps and isinstance(steps[0], dict) else {}
    args = dict(step0.get("args") or {}) if isinstance(step0, dict) else {}
    first_output = ""
    for item in step_outputs:
        if isinstance(item, dict) and str(item.get("output") or "").strip():
            first_output = str(item.get("output") or "").strip()
            break

    cap = (primary_capability or str(step0.get("capability") or "")).strip()
    if cap == "notes.create":
        path = ""
        if first_output.lower().startswith("created note "):
            path = first_output[len("created note ") :].strip()
        path = path or str(args.get("path") or args.get("body") or goal)[:120]
        nodes.append(
            {
                "id": f"note:{path or request_id}",
                "type": "note",
                "attributes": {
                    "title": path or goal,
                    "path": path,
                    "receipt_id": receipt_id,
                    "request_id": request_id,
                },
            }
        )
    elif cap == "notes.search":
        query = str(args.get("query") or goal)
        nodes.append(
            {
                "id": f"note_search:{request_id}",
                "type": "note",
                "attributes": {
                    "title": f"search:{query}",
                    "query": query,
                    "receipt_id": receipt_id,
                    "request_id": request_id,
                },
            }
        )
    elif cap == "memory.store":
        body = str(args.get("body") or goal)
        label = body.split("|", 1)[0].strip() if "|" in body else body.split(" ", 1)[0]
        nodes.append(
            {
                "id": f"memory:{label or request_id}",
                "type": "memory",
                "attributes": {
                    "label": label,
                    "content": body,
                    "receipt_id": receipt_id,
                    "request_id": request_id,
                },
            }
        )
    elif cap == "memory.query":
        query = str(args.get("query") or goal)
        nodes.append(
            {
                "id": f"memory_query:{request_id}",
                "type": "memory",
                "attributes": {
                    "label": f"query:{query}",
                    "query": query,
                    "receipt_id": receipt_id,
                    "request_id": request_id,
                },
            }
        )
    elif cap == "launch_application":
        app = str(args.get("application") or goal).strip().lower()
        if app:
            nodes.append(
                {
                    "id": f"application:{app}",
                    "type": "application",
                    "attributes": {
                        "name": app,
                        "receipt_id": receipt_id,
                        "request_id": request_id,
                    },
                }
            )
    elif cap == "navigate":
        view = str(args.get("view") or "home").strip().lower()
        nodes.append(
            {
                "id": f"navigate:{view}:{request_id}",
                "type": "workspace",
                "attributes": {
                    "view": view,
                    "receipt_id": receipt_id,
                    "request_id": request_id,
                },
            }
        )
    return nodes
