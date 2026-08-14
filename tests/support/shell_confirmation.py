"""Test helpers for shell confirmation gates (ADR-009 / control-plane)."""

from __future__ import annotations

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import TOOL_APPROVED, TOOL_CONFIRMATION_REQUIRED

TRUSTED_UI_RUN = {"interactive_user": True, "actor_provenance": "ui"}


def wire_auto_confirm_shell(bus: EventBus) -> None:
    """Auto-approve shell confirmations in tests that drive UI shell to completion."""

    def _on_confirm(event) -> None:
        cid = str(event.payload.get("confirmation_id") or "")
        if not cid or ":" not in cid:
            return
        run_id, step_id = cid.split(":", 1)
        bus.publish(
            TOOL_APPROVED,
            {
                "confirmation_id": cid,
                "run_id": run_id,
                "step_id": step_id,
                "approved": True,
            },
            source="ui",
        )

    bus.subscribe(TOOL_CONFIRMATION_REQUIRED, _on_confirm)
