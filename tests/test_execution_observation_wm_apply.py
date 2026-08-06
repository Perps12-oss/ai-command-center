"""BrainRuntime applies execution.observation facts to World Model (ADR-019)."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    EXECUTION_OBSERVATION,
    RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
)
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.repositories.world_model_repository import SQLiteWorldModelRepository
from ai_command_center.services.brain_runtime_service import BrainRuntimeService


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_execution_observation_applies_wm_node() -> None:
    bus = EventBus()
    repo = SQLiteWorldModelRepository(_conn())
    wm = WorldModel(repo)
    runtime = BrainRuntimeService(bus, wm)
    runtime.start()
    completed: list[dict] = []
    bus.subscribe(
        RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
        lambda e: completed.append(dict(e.payload)),
    )
    try:
        bus.publish(
            EXECUTION_OBSERVATION,
            {
                "run_id": "run-1",
                "step_id": "s1",
                "step_index": 0,
                "capability": "shell",
                "success": True,
                "output": "ok",
                "args": {"command": "echo hi"},
            },
            source="test",
        )
        assert completed
        node = wm.get_node("execution_obs:run-1:s1")
        assert node is not None
        assert node.type == "execution_observation"
        assert node.attributes.get("capability") == "shell"
    finally:
        runtime.stop()
