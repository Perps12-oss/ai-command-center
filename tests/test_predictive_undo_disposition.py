"""R1 P5 — PredictiveEngine / UndoReplay disposition pins (ADR-014)."""

from __future__ import annotations

import inspect
import sqlite3

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.service_factory import build_services
from ai_command_center.core.world_model.predictive_engine import PredictiveEngine
from ai_command_center.core.world_model.undo_replay import Timeline
from ai_command_center.db.connection import init_database


def test_build_services_does_not_wire_predictive_or_undo_replay() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    bus = EventBus()
    wired = build_services(conn, bus, workspace_os_enabled=False)
    names = set(wired.services.names())
    assert "predictive_engine" not in names
    assert "undo_replay" not in names
    source = inspect.getsource(build_services)
    assert "PredictiveEngine" not in source
    assert "undo_replay" not in source


def test_research_packages_importable_for_unit_tests() -> None:
    """Tree remains for research/unit tests — ADR-014 does not delete packages."""
    assert PredictiveEngine is not None
    assert Timeline is not None
