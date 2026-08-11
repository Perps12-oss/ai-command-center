"""B3 — authority decisions must not pollute user-facing chat state (Inv 4).

Authority decisions are operational state; chat state is presentation state.
A programmatic intake carries goal text such as ``workflow:demo``, which the
baseline reducer accepted as a pending user chat bubble.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_command_center.core.contracts import (
    INTAKE_AGENT,
    INTAKE_UI_COMMAND,
    INTAKE_WORKFLOW,
)
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import EXECUTION_AUTHORITY_DECISION
from ai_command_center.core.state.chat_state import _reduce_authority_decision


@dataclass(frozen=True)
class _ChatState:
    """Minimal stand-in exposing the fields the reducer writes (uses dataclasses.replace)."""

    last_command: str = ""
    last_command_intent: str = ""
    chat_pending_user_text: str = ""
    last_event_topic: str = ""
    last_event_source: str = ""
    last_workspace_context_workspace_id: str = ""


def _decide(payload: dict) -> _ChatState:
    return _reduce_authority_decision(
        _ChatState(),
        Event(topic=EXECUTION_AUTHORITY_DECISION, payload=payload, source="execution_authority"),
    )


def test_workflow_decision_does_not_touch_chat_state() -> None:
    """`workflow:demo` passes _is_pending_chat_user_text — it must be excluded by intake."""
    state = _decide(
        {
            "request_id": "r1",
            "intake": INTAKE_WORKFLOW,
            "text": "workflow:demo",
            "capability": "workflow",
        }
    )
    assert state.chat_pending_user_text == "", "workflow goal leaked into chat bubble"
    assert state.last_command == "", "workflow goal leaked into last_command"
    assert state.last_command_intent == ""


def test_agent_decision_with_real_task_does_not_touch_chat_state() -> None:
    """Agent goal is `task or agent:<id>` — a real task is not prefix-filtered."""
    state = _decide(
        {
            "request_id": "r2",
            "intake": INTAKE_AGENT,
            "text": "summarise the quarterly report",
            "capability": "agent.shell",
        }
    )
    assert state.chat_pending_user_text == "", "agent task leaked into chat bubble"
    assert state.last_command == "", "agent task leaked into last_command"


def test_ui_command_decision_still_populates_chat_state() -> None:
    """Guard against over-correction: real chat commands must still flow."""
    state = _decide(
        {
            "request_id": "r3",
            "intake": INTAKE_UI_COMMAND,
            "text": "What is Python?",
            "capability": "llm",
        }
    )
    assert state.chat_pending_user_text == "What is Python?"
    assert state.last_command == "What is Python?"
    assert state.last_command_intent == "llm"


def test_decision_without_intake_is_treated_as_user_command() -> None:
    """Backward compatibility: pre-contract payloads keep established behaviour."""
    state = _decide({"request_id": "r4", "text": "What is Python?", "capability": "llm"})
    assert state.chat_pending_user_text == "What is Python?"
    assert state.last_command == "What is Python?"
