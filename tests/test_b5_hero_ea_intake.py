"""B5 — Hero New Goal must enter via EA; GOAL_SUBMIT_REQUEST is post-authority only."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_AUTHORITY_DECISION,
    GOAL_SUBMIT_REQUEST,
    GOAL_SUBMITTED,
    UI_COMMAND,
    WORKSPACE_ACTIVE,
)
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.services.execution_authority_service import ExecutionAuthorityService
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.ui.controller import UIController


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_goal_intake_hero_new_goal_publishes_ui_command_not_goal_submit() -> None:
    """Controller must not emit the scheduler topic (B5 fork 1)."""
    bus = EventBus()
    ctrl = UIController(bus, AppStateStore(bus), on_state=lambda: None)
    commands: list[dict] = []
    submits: list[dict] = []
    bus.subscribe(UI_COMMAND, lambda e: commands.append(dict(e.payload)))
    bus.subscribe(GOAL_SUBMIT_REQUEST, lambda e: submits.append(dict(e.payload)))

    ctrl.publish_goal_submit_request("Ship B5", priority=1, description="hero")

    assert len(commands) == 1
    assert commands[0]["text"].lower().startswith("goal:")
    assert "Ship B5" in commands[0]["text"]
    assert commands[0]["priority"] == 1
    assert commands[0]["description"] == "hero"
    assert submits == [], "UI must not publish GOAL_SUBMIT_REQUEST"


def test_goal_intake_hero_reaches_scheduler_only_after_ea_admission() -> None:
    """Hero → UI_COMMAND → EXECUTION_AUTHORITY_DECISION → stamped GOAL_SUBMIT_REQUEST."""
    bus = EventBus()
    ExecutionAuthorityService(bus).start()
    SingleGoalScheduler(bus, GoalRepository(_conn())).start()

    order: list[str] = []
    decisions: list[dict] = []
    submits: list[dict] = []
    submitted_facts: list[dict] = []

    bus.subscribe(
        EXECUTION_AUTHORITY_DECISION,
        lambda e: (order.append(e.topic), decisions.append(dict(e.payload))),
    )
    bus.subscribe(
        GOAL_SUBMIT_REQUEST,
        lambda e: (order.append(e.topic), submits.append(dict(e.payload))),
    )
    bus.subscribe(GOAL_SUBMITTED, lambda e: submitted_facts.append(dict(e.payload)))

    bus.publish(WORKSPACE_ACTIVE, {"workspace_id": "ws-b5"}, source="test")
    ctrl = UIController(bus, AppStateStore(bus), on_state=lambda: None)
    ctrl.publish_goal_submit_request("New Goal", priority=0)

    assert decisions, "EA must publish EXECUTION_AUTHORITY_DECISION"
    assert decisions[0]["capability"] == "goal"
    assert decisions[0]["intake"] == "ui_command"
    assert "state_context" in decisions[0]
    assert submits, "EA must emit GOAL_SUBMIT_REQUEST after admission"
    assert isinstance(submits[0].get("authority_decision"), dict)
    assert submits[0]["authority_decision"]
    assert submits[0]["title"] == "New Goal"
    assert order.index(EXECUTION_AUTHORITY_DECISION) < order.index(GOAL_SUBMIT_REQUEST)
    assert submitted_facts, "scheduler must accept EA-stamped submit"


def test_goal_intake_hero_direct_submit_without_authority_decision_is_refused() -> None:
    """Fail-closed: bypass publish cannot admit into SingleGoalScheduler."""
    bus = EventBus()
    SingleGoalScheduler(bus, GoalRepository(_conn())).start()
    facts: list[dict] = []
    bus.subscribe(GOAL_SUBMITTED, lambda e: facts.append(dict(e.payload)))

    bus.publish(
        GOAL_SUBMIT_REQUEST,
        {"title": "Bypass Goal", "goal": "Bypass Goal", "priority": 0},
        source="ui",
    )

    assert facts == [], "scheduler must refuse GOAL_SUBMIT_REQUEST without authority_decision"
