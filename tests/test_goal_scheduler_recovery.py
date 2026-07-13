"""Phase 9 restart-recovery tests for SingleGoalScheduler.

Verifies that goals persisted to SQLite survive a simulated restart:
- QUEUED goals are reloaded into the in-memory queue.
- ACTIVE goals (crashed mid-run) are downgraded to QUEUED and re-queued.
- A fresh scheduler instance on the same DB behaves as if nothing was lost.
"""

from __future__ import annotations

import sqlite3

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import GOAL_ACTIVATED, GOAL_SUBMITTED
from ai_command_center.domain.goal import Goal, GoalStatus, Priority
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.services.goal_scheduler_service import SingleGoalScheduler


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    return c


def _goal(goal_id: str, title: str = "Test", priority: Priority = Priority.NORMAL) -> Goal:
    correlation = CorrelationContext.new(goal_id=goal_id)
    return Goal(
        id=goal_id,
        title=title,
        description="",
        priority=priority,
        correlation=correlation.with_goal(goal_id),
    )


# ── helpers ────────────────────────────────────────────────────────────────


def _start(bus: EventBus, repo: GoalRepository) -> SingleGoalScheduler:
    s = SingleGoalScheduler(bus, repo)
    s.start()
    return s


def _stop(scheduler: SingleGoalScheduler) -> None:
    scheduler.stop()


# ── tests ──────────────────────────────────────────────────────────────────


def test_queued_goal_survives_restart() -> None:
    """A QUEUED goal written in session 1 is present in session 2's queue."""
    conn = _conn()
    repo = GoalRepository(conn)
    bus1 = EventBus()

    # Session 1: submit a goal, then immediately stop before it activates
    s1 = _start(bus1, repo)
    # Bypass the activation logic: write QUEUED directly to repo
    goal = _goal("g-queued")
    queued_goal = Goal(
        id=goal.id,
        title=goal.title,
        description=goal.description,
        priority=goal.priority,
        status=GoalStatus.QUEUED,
        correlation=goal.correlation,
    )
    repo.save_goal(queued_goal)
    _stop(s1)

    # Session 2: new scheduler on same conn — should pick up the queued goal
    bus2 = EventBus()
    activated: list[dict] = []
    bus2.subscribe(GOAL_ACTIVATED, lambda e: activated.append(dict(e.payload)))

    s2 = _start(bus2, repo)
    _stop(s2)

    # The recovered goal must have been activated
    assert len(activated) == 1
    assert activated[0]["goal"]["id"] == "g-queued"


def test_active_goal_at_crash_is_downgraded_and_requeued() -> None:
    """A goal left ACTIVE (crash mid-run) is downgraded to QUEUED on restart."""
    conn = _conn()
    repo = GoalRepository(conn)
    bus1 = EventBus()

    # Simulate a crash: write an ACTIVE goal directly to the DB
    goal = _goal("g-crashed")
    active_goal = Goal(
        id=goal.id,
        title=goal.title,
        description=goal.description,
        priority=goal.priority,
        status=GoalStatus.ACTIVE,
        correlation=goal.correlation,
    )
    repo.save_goal(active_goal)

    # Verify it's ACTIVE before recovery
    assert repo.get_goal("g-crashed").status == GoalStatus.ACTIVE

    # Session 2: recovery must downgrade ACTIVE → QUEUED and then activate
    bus2 = EventBus()
    activated: list[dict] = []
    bus2.subscribe(GOAL_ACTIVATED, lambda e: activated.append(dict(e.payload)))

    s2 = _start(bus2, repo)
    _stop(s2)

    # Goal was downgraded in the repo then re-activated
    assert len(activated) == 1
    assert activated[0]["goal"]["id"] == "g-crashed"


def test_multiple_queued_goals_recover_in_priority_order() -> None:
    """Multiple QUEUED goals recovered in CRITICAL > HIGH > NORMAL > LOW order."""
    conn = _conn()
    repo = GoalRepository(conn)

    # Write three goals with different priorities directly
    for goal_id, priority in [
        ("g-low", Priority.LOW),
        ("g-critical", Priority.CRITICAL),
        ("g-normal", Priority.NORMAL),
    ]:
        g = _goal(goal_id, priority=priority)
        repo.save_goal(
            Goal(
                id=g.id,
                title=g.title,
                description="",
                priority=priority,
                status=GoalStatus.QUEUED,
                correlation=g.correlation,
            )
        )

    bus = EventBus()
    activated: list[dict] = []
    bus.subscribe(GOAL_ACTIVATED, lambda e: activated.append(dict(e.payload)))

    s = _start(bus, repo)
    _stop(s)

    # Only the highest-priority goal activates immediately on startup
    assert len(activated) == 1
    assert activated[0]["goal"]["id"] == "g-critical"


def test_completed_goals_are_not_requeued() -> None:
    """COMPLETE and FAILED goals must not be recovered into the queue."""
    conn = _conn()
    repo = GoalRepository(conn)

    for goal_id, status in [
        ("g-complete", GoalStatus.COMPLETE),
        ("g-failed", GoalStatus.FAILED),
        ("g-cancelled", GoalStatus.CANCELLED),
    ]:
        g = _goal(goal_id)
        repo.save_goal(
            Goal(
                id=g.id,
                title=g.title,
                description="",
                priority=g.priority,
                status=status,
                correlation=g.correlation,
            )
        )

    bus = EventBus()
    activated: list[dict] = []
    bus.subscribe(GOAL_ACTIVATED, lambda e: activated.append(dict(e.payload)))

    s = _start(bus, repo)
    _stop(s)

    assert activated == [], "Terminal goals must never be requeued"


def test_empty_db_on_restart_is_safe() -> None:
    """Recovery with an empty DB must not raise or activate anything."""
    conn = _conn()
    repo = GoalRepository(conn)
    bus = EventBus()
    activated: list[dict] = []
    bus.subscribe(GOAL_ACTIVATED, lambda e: activated.append(dict(e.payload)))

    s = _start(bus, repo)
    _stop(s)

    assert activated == []


def test_fresh_goal_still_activates_after_recovery() -> None:
    """After recovery, newly submitted goals still activate correctly."""
    conn = _conn()
    repo = GoalRepository(conn)
    bus = EventBus()

    activated: list[dict] = []
    bus.subscribe(GOAL_ACTIVATED, lambda e: activated.append(dict(e.payload)))

    s = _start(bus, repo)
    s.submit_goal(_goal("g-new"))
    _stop(s)

    assert len(activated) == 1
    assert activated[0]["goal"]["id"] == "g-new"
