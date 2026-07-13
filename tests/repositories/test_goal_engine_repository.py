"""Unit tests for SQLiteGoalEngineRepository — Phase 9 persistence."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from ai_command_center.orchestration.goals.goal import Goal
from ai_command_center.orchestration.goals.goal_status import GoalStatus
from ai_command_center.repositories.goal_engine_repository import SQLiteGoalEngineRepository


@pytest.fixture
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    return c


@pytest.fixture
def repo(conn: sqlite3.Connection) -> SQLiteGoalEngineRepository:
    return SQLiteGoalEngineRepository(conn)


def _goal(
    goal_id: str = "g-1",
    title: str = "Test Goal",
    status: GoalStatus = GoalStatus.DRAFT,
    parent: str | None = None,
    priority: int = 0,
    tags: list[str] | None = None,
) -> Goal:
    return Goal(
        id=goal_id,
        title=title,
        description="test description",
        status=status,
        created_by="test",
        parent_goal_id=parent,
        tags=tags or [],
        priority=priority,
    )


# ── save / get round-trip ──────────────────────────────────────────────────


def test_save_and_get_round_trip(repo: SQLiteGoalEngineRepository) -> None:
    goal = _goal()
    repo.save(goal)
    retrieved = repo.get("g-1")
    assert retrieved is not None
    assert retrieved.id == "g-1"
    assert retrieved.title == "Test Goal"
    assert retrieved.status == GoalStatus.DRAFT
    assert retrieved.created_by == "test"


def test_get_nonexistent_returns_none(repo: SQLiteGoalEngineRepository) -> None:
    assert repo.get("does-not-exist") is None


def test_save_is_idempotent_upsert(repo: SQLiteGoalEngineRepository) -> None:
    goal = _goal()
    repo.save(goal)
    activated = goal.activate()
    repo.save(activated)
    retrieved = repo.get("g-1")
    assert retrieved is not None
    assert retrieved.status == GoalStatus.ACTIVE


def test_tags_survive_round_trip(repo: SQLiteGoalEngineRepository) -> None:
    goal = _goal(tags=["urgent", "phase-9", "backend"])
    repo.save(goal)
    retrieved = repo.get("g-1")
    assert retrieved is not None
    assert set(retrieved.tags) == {"urgent", "phase-9", "backend"}


def test_metadata_survives_round_trip(repo: SQLiteGoalEngineRepository) -> None:
    goal = Goal(
        id="g-meta",
        title="Meta goal",
        description="",
        metadata={"source": "audit", "confidence": 0.95},
    )
    repo.save(goal)
    retrieved = repo.get("g-meta")
    assert retrieved is not None
    assert retrieved.metadata["source"] == "audit"
    assert retrieved.metadata["confidence"] == pytest.approx(0.95)


def test_priority_survives_round_trip(repo: SQLiteGoalEngineRepository) -> None:
    goal = _goal(priority=42)
    repo.save(goal)
    retrieved = repo.get("g-1")
    assert retrieved is not None
    assert retrieved.priority == 42


def test_deadline_survives_round_trip(repo: SQLiteGoalEngineRepository) -> None:
    dl = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    goal = Goal(id="g-dl", title="Deadline goal", description="", deadline=dl)
    repo.save(goal)
    retrieved = repo.get("g-dl")
    assert retrieved is not None
    assert retrieved.deadline is not None
    assert retrieved.deadline.year == 2026
    assert retrieved.deadline.month == 12


def test_no_deadline_survives_round_trip(repo: SQLiteGoalEngineRepository) -> None:
    goal = Goal(id="g-nodl", title="No deadline", description="")
    repo.save(goal)
    retrieved = repo.get("g-nodl")
    assert retrieved is not None
    assert retrieved.deadline is None


# ── get_by_status ──────────────────────────────────────────────────────────


def test_get_by_status_returns_matching(repo: SQLiteGoalEngineRepository) -> None:
    repo.save(_goal("g-1", status=GoalStatus.DRAFT))
    repo.save(_goal("g-2", status=GoalStatus.ACTIVE))
    repo.save(_goal("g-3", status=GoalStatus.DRAFT))
    drafts = repo.get_by_status(GoalStatus.DRAFT)
    assert len(drafts) == 2
    assert {g.id for g in drafts} == {"g-1", "g-3"}


def test_get_by_status_empty(repo: SQLiteGoalEngineRepository) -> None:
    repo.save(_goal("g-1", status=GoalStatus.DRAFT))
    assert repo.get_by_status(GoalStatus.COMPLETED) == []


# ── get_active ─────────────────────────────────────────────────────────────


def test_get_active_excludes_terminal(repo: SQLiteGoalEngineRepository) -> None:
    repo.save(_goal("g-draft", status=GoalStatus.DRAFT))
    repo.save(_goal("g-active", status=GoalStatus.ACTIVE))
    repo.save(_goal("g-paused", status=GoalStatus.PAUSED))
    repo.save(_goal("g-completed", status=GoalStatus.COMPLETED))
    repo.save(_goal("g-failed", status=GoalStatus.FAILED))
    repo.save(_goal("g-abandoned", status=GoalStatus.ABANDONED))
    active = repo.get_active()
    ids = {g.id for g in active}
    assert "g-draft" in ids
    assert "g-active" in ids
    assert "g-paused" in ids
    assert "g-completed" not in ids
    assert "g-failed" not in ids
    assert "g-abandoned" not in ids


# ── hierarchy ──────────────────────────────────────────────────────────────


def test_get_children(repo: SQLiteGoalEngineRepository) -> None:
    repo.save(_goal("root"))
    repo.save(_goal("child-1", parent="root"))
    repo.save(_goal("child-2", parent="root"))
    repo.save(_goal("unrelated"))
    children = repo.get_children("root")
    assert len(children) == 2
    assert {c.id for c in children} == {"child-1", "child-2"}


def test_get_root_goals(repo: SQLiteGoalEngineRepository) -> None:
    repo.save(_goal("root-1"))
    repo.save(_goal("root-2"))
    repo.save(_goal("child", parent="root-1"))
    roots = repo.get_root_goals()
    assert len(roots) == 2
    assert {g.id for g in roots} == {"root-1", "root-2"}


def test_get_children_empty(repo: SQLiteGoalEngineRepository) -> None:
    repo.save(_goal("root"))
    assert repo.get_children("root") == []


# ── delete ─────────────────────────────────────────────────────────────────


def test_delete_existing_returns_true(repo: SQLiteGoalEngineRepository) -> None:
    repo.save(_goal("g-1"))
    assert repo.delete("g-1") is True
    assert repo.get("g-1") is None


def test_delete_nonexistent_returns_false(repo: SQLiteGoalEngineRepository) -> None:
    assert repo.delete("ghost") is False


def test_delete_does_not_affect_siblings(repo: SQLiteGoalEngineRepository) -> None:
    repo.save(_goal("g-1"))
    repo.save(_goal("g-2"))
    repo.delete("g-1")
    assert repo.get("g-2") is not None


# ── schema idempotency ─────────────────────────────────────────────────────


def test_second_repo_on_same_conn_does_not_break(conn: sqlite3.Connection) -> None:
    r1 = SQLiteGoalEngineRepository(conn)
    r1.save(_goal("g-1"))
    r2 = SQLiteGoalEngineRepository(conn)
    retrieved = r2.get("g-1")
    assert retrieved is not None
    assert retrieved.title == "Test Goal"
