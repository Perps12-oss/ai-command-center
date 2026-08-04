"""Stage 2 + ADR-016 — Goals SA soft-shadow / mutate pins."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import WORLD_MODEL_MUTATION_APPLIED
from ai_command_center.core.service_factory import build_services
from ai_command_center.db.connection import init_database
from ai_command_center.domain.state_authority import StateDelta, StateQuery
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler
from ai_command_center.services.state_authority_service import StateAuthorityService


def test_build_services_wires_goal_submit_for_state() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    sa = wired.services.get("state_authority")
    assert isinstance(sa, StateAuthorityService)
    assert sa._goal_submit is not None
    assert (
        getattr(sa._goal_submit, "__func__", None)
        is SingleGoalScheduler.submit_goal_for_state
    )


def test_sa_mutate_submit_goal_round_trip() -> None:
    """ADR-016: submit_goal via SA.mutate → goals table; no WM dual-write."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    sa = wired.services.get("state_authority")
    scheduler = wired.services.get("single_goal_scheduler")
    assert isinstance(sa, StateAuthorityService)
    assert isinstance(scheduler, SingleGoalScheduler)

    wm_events: list[str] = []
    bus.subscribe(WORLD_MODEL_MUTATION_APPLIED, lambda e: wm_events.append(e.topic))

    scheduler.start()
    sa.start()
    receipt = sa.mutate(
        StateDelta(
            workspace_id="ws-g",
            operations=(
                {
                    "op": "submit_goal",
                    "title": "ADR016 pin ship mango",
                    "description": "soft-shadow mutate",
                },
            ),
        )
    )
    assert receipt.ok is True
    assert receipt.applied
    assert receipt.applied[0]["op"] == "submit_goal"
    assert receipt.applied[0].get("goal_id")
    assert wm_events == []

    projection = sa.query(
        StateQuery(text="mango", workspace_id="ws-g", include_goals=True)
    )
    assert projection.goals
    blob = " ".join(str(g) for g in projection.goals).lower()
    assert "mango" in blob
    sa.stop()
    scheduler.stop()


def test_sa_mutate_submit_goal_rejects_empty_title() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    sa = wired.services.get("state_authority")
    assert isinstance(sa, StateAuthorityService)
    sa.start()
    receipt = sa.mutate(
        StateDelta(
            workspace_id="ws-g",
            operations=({"op": "submit_goal", "title": ""},),
        )
    )
    assert receipt.ok is False
    assert "title required" in receipt.message.lower()
    sa.stop()


def test_sa_mutate_still_rejects_create_goal_alias() -> None:
    """Only submit_goal is accepted — create_goal remains unsupported."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    sa = wired.services.get("state_authority")
    assert isinstance(sa, StateAuthorityService)
    sa.start()
    receipt = sa.mutate(
        StateDelta(
            workspace_id="ws-g",
            operations=({"op": "create_goal", "title": "nope"},),
        )
    )
    assert receipt.ok is False
    assert "unsupported" in receipt.message.lower()
    sa.stop()
