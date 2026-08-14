"""Sync receipt + truth emission for the execution completion boundary.

Single owner (Inv 11) of *how* an ``ExecutionReceipt`` is built and published.
``ExecutionOrchestratorService`` calls this **before** ``EXECUTION_RUN_COMPLETE``
so public success cannot precede evidence. ``OrchestrationService`` reuses the
same helper on failure (and on COMPLETE fanout when receipt was not pre-emitted).

This deliberately avoids a new EventBus topic: ``ORCHESTRATION_RECEIPT`` already
dispatches inline (``SYNC_STANDARD``), so the orchestrator ledger is updated
before ``publish()`` returns.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from ai_command_center.core.events.topics import (
    ORCHESTRATION_RECEIPT,
    ORCHESTRATION_TRUTH_VALIDATED,
)
from ai_command_center.orchestration.receipts.execution_receipt import ExecutionReceipt
from ai_command_center.orchestration.verification.execution_truth import (
    enrich_execution_facts,
    validate_execution_truth,
)

_logger = logging.getLogger(__name__)

# Stable bus source for receipt evidence (contract consumers filter on this).
RECEIPT_BUS_SOURCE = "orchestration"


def _primary_capability(payload: dict[str, Any]) -> str:
    plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
    steps = list(plan.get("steps") or [])
    step_outputs = list(payload.get("step_outputs") or [])
    if steps and isinstance(steps[0], dict):
        return str(steps[0].get("capability") or "")
    if step_outputs and isinstance(step_outputs[0], dict):
        return str(step_outputs[0].get("capability") or "")
    return ""


def _compose_response_text(
    step_outputs: list[object],
    *,
    success: bool,
    error: str,
) -> str:
    texts: list[str] = []
    for item in step_outputs:
        if not isinstance(item, dict):
            continue
        output = str(item.get("output") or "").strip()
        if output:
            texts.append(output)
        elif not item.get("success", True):
            step_error = str(item.get("error") or "").strip()
            if step_error:
                texts.append(step_error)
    if texts:
        return "\n".join(texts)
    if success:
        return "Done."
    return f"I could not complete that action: {error or 'execution failed'}"


def resolve_completion_request_id(payload: dict[str, Any]) -> str:
    """Return correlating id, synthesizing one when absent (G1)."""
    request_id = str(payload.get("request_id") or payload.get("run_id") or "").strip()
    if request_id:
        return request_id
    request_id = uuid.uuid4().hex
    _logger.warning(
        "orchestration.completion missing request_id/run_id — "
        "synthesized request_id=%s to preserve receipt boundary",
        request_id,
    )
    return request_id


def emit_execution_receipt(
    bus: Any,
    *,
    payload: dict[str, Any],
    success: bool,
    error: str = "",
    source: str = RECEIPT_BUS_SOURCE,
) -> dict[str, Any] | None:
    """Publish ``ORCHESTRATION_RECEIPT`` + truth. Return evidence dict or None.

    On success the returned dict includes ``request_id``, ``receipt_id``, and
    fields the COMPLETE fanout needs so OrchestrationService can skip a second
    receipt.
    """
    try:
        request_id = resolve_completion_request_id(payload)
        run_id = str(payload.get("run_id", "")).strip()
        goal = str(payload.get("goal") or "")
        step_outputs = list(payload.get("step_outputs") or [])
        plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
        steps = list(plan.get("steps") or [])
        primary_capability = _primary_capability(payload)

        response_text = _compose_response_text(
            step_outputs, success=success, error=error
        )
        facts: dict[str, object] = {
            "run_id": run_id,
            "goal": goal,
            "capability": primary_capability,
            "step_count": len(step_outputs) or len(steps),
            "step_outputs": step_outputs,
            "success": success,
        }
        if error:
            facts["error"] = error
        facts = enrich_execution_facts(
            facts=facts,
            plan=plan if isinstance(plan, dict) else {},
            step_outputs=step_outputs,
            success=success,
        )

        workspace_context = (
            payload.get("workspace_context")
            if isinstance(payload.get("workspace_context"), dict)
            else {}
        )
        workspace_id = str(
            workspace_context.get("workspace_id") or payload.get("workspace_id") or ""
        ).strip()
        entity_id = str(workspace_context.get("entity_id") or "").strip()
        scope_fields: dict[str, str] = {}
        if workspace_id:
            scope_fields["workspace_id"] = workspace_id
        if entity_id:
            scope_fields["entity_id"] = entity_id

        receipt = ExecutionReceipt(
            receipt_id=uuid.uuid4().hex,
            request_id=request_id,
            intent=primary_capability or "execution_run",
            provider_id="execution_orchestrator",
            success=success,
            facts=tuple(sorted(facts.items(), key=lambda item: item[0])),
            error=error or None,
        )
        bus.publish(ORCHESTRATION_RECEIPT, receipt.to_dict(), source=source)

        validation = validate_execution_truth(
            capability=primary_capability,
            success=success,
            error=error,
            response_text=response_text,
            facts=facts,
            receipt=receipt,
        )
        truth_valid = bool(validation.valid)
        truth_detail = validation.detail
        response_source = validation.response_source
        response_text = validation.response_text or response_text
        bus.publish(
            ORCHESTRATION_TRUTH_VALIDATED,
            {
                "request_id": request_id,
                "valid": truth_valid,
                "detail": truth_detail,
                "response_source": response_source,
                "run_id": run_id,
                **scope_fields,
            },
            source=source,
        )
        return {
            "request_id": request_id,
            "receipt_id": receipt.receipt_id,
            "run_id": run_id,
            "goal": goal,
            "primary_capability": primary_capability,
            "facts": facts,
            "truth_valid": truth_valid,
            "truth_detail": truth_detail,
            "response_source": response_source,
            "response_text": response_text,
            "scope_fields": scope_fields,
            "receipt_already_emitted": True,
        }
    except Exception:
        _logger.exception("orchestration.receipt_emit_failed")
        return None


__all__ = [
    "RECEIPT_BUS_SOURCE",
    "emit_execution_receipt",
    "resolve_completion_request_id",
]
