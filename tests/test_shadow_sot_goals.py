"""Stage 2 Slice 3 — Goals dual-path quarantine + SA goal projection."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.service_factory import build_services
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.db.connection import init_database
from ai_command_center.domain.goal import Goal, GoalStatus
from ai_command_center.domain.state_authority import StateQuery
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.repositories.world_model_repository import SQLiteWorldModelRepository
from ai_command_center.services.state_authority_service import StateAuthorityService


def test_build_services_does_not_wire_goal_engine() -> None:
    """Phase-9 GoalEngine must not be on the live composition root."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    assert not hasattr(wired, "goal_engine")
    names = set(wired.services.names())
    assert "goal_engine" not in names
    assert "single_goal_scheduler" in names
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "goal_engine_goals" not in tables
    assert "goals" in tables


def test_state_authority_goal_lookup_projects_goal_repository() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    goal_repo = GoalRepository(conn)
    goal_repo.save_goal(
        Goal(
            id="g-live-1",
            title="Ship Slice 3",
            status=GoalStatus.ACTIVE,
        )
    )

    def _lookup(*, workspace_id: str = "") -> list[dict]:
        return [
            {
                "id": g.id,
                "title": g.title,
                "status": g.status.value if hasattr(g.status, "value") else str(g.status),
                "workspace_id": workspace_id,
            }
            for g in goal_repo.list_goals()
        ]

    wm = WorldModel(SQLiteWorldModelRepository(conn))
    bus = EventBus()
    sa = StateAuthorityService(bus, wm, goal_lookup=_lookup)
    proj = sa.query(StateQuery(text="Ship", include_goals=True))
    assert any(g.get("id") == "g-live-1" for g in proj.goals)
