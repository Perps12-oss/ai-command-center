"""Component tests for the global context bar."""

from __future__ import annotations

import pytest

from ai_command_center.core.app_state import AppState
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import UI_CONTEXT_CLEAR, UI_CONTEXT_SELECT
from ai_command_center.core.state.global_context_state import (
    GlobalContextSnapshot,
    reduce_global_context_state,
)
from ai_command_center.domain.settings_snapshot import SettingsSnapshot
from ai_command_center.ui.controller import UIController
from tests.ui.fake_ui import GlobalContextBar


def _make_state(**kwargs: object) -> AppState:
    defaults: dict[str, object] = {
        "settings": SettingsSnapshot(),
        "global_context": GlobalContextSnapshot(),
    }
    defaults.update(kwargs)
    return AppState(**defaults)


@pytest.fixture
def context_bar():
    """Return a fake-bound GlobalContextBar instance."""
    return GlobalContextBar(None)


def test_context_bar_shows_workspace_entity_and_sources(context_bar):
    """GlobalContextBar projects workspace, entity, sources, tokens, and model."""
    snap = _make_state(
        global_context=GlobalContextSnapshot(
            workspace_title="Test Workspace",
            entity_title="Selected Card",
            active_goal_title="Ship Stage 1",
            sources=("note-1", "memory-2"),
            token_estimate=2048,
        ),
        settings=SettingsSnapshot(default_model="gpt-4", provider="openai"),
    )
    context_bar.update(snap)

    assert "Test Workspace" in context_bar._scope_label.cget("text")
    assert "Selected Card" in context_bar._scope_label.cget("text")
    assert "Ship Stage 1" in context_bar._goal_label.cget("text")
    assert "note-1" in context_bar._sources_label.cget("text")
    assert "memory-2" in context_bar._sources_label.cget("text")
    assert "2048 tokens" in context_bar._tokens_label.cget("text")
    assert "gpt-4" in context_bar._model_label.cget("text")


def test_context_bar_empty_state(context_bar):
    """When no context is active the bar shows informative empty state."""
    snap = _make_state()
    context_bar.update(snap)

    assert "No active workspace" in context_bar._scope_label.cget("text")
    assert "No active goal" in context_bar._goal_label.cget("text")
    assert "No context sources" in context_bar._sources_label.cget("text")
    assert context_bar._tokens_label.cget("text") == ""


def test_context_bar_projects_active_goal_from_brain_state(context_bar):
    """Bar falls back to brain_state.recent_goals when snapshot goal is empty."""
    from ai_command_center.domain.brain_state_snapshot import (
        BrainStateSnapshot,
        GoalSnapshot,
    )

    snap = _make_state(
        brain_state=BrainStateSnapshot(
            recent_goals=(
                GoalSnapshot(goal_id="g1", text="Active from brain", status="active"),
            ),
        ),
    )
    context_bar.update(snap)
    assert "Active from brain" in context_bar._goal_label.cget("text")


def test_global_context_reducer_updates_from_context_snapshot():
    """reduce_global_context_state promotes context snapshot to global state."""
    state = _make_state()
    event = type("Event", (), {
        "topic": "context.snapshot_created",
        "payload": {
            "sources": ["note-a", "memory-b"],
            "context_size_tokens": 1024,
            "workspace_id": "ws-1",
        },
        "source": "tests",
        "timestamp": 0.0,
    })()
    new_state = reduce_global_context_state(state, event)
    assert new_state.global_context.sources == ("note-a", "memory-b")
    assert new_state.global_context.token_estimate == 1024
    assert new_state.global_context.workspace_id == "ws-1"
    assert new_state.global_context.revision == 1


def test_global_context_reducer_updates_from_workspace_active():
    """Workspace activation updates the global context workspace."""
    state = _make_state()
    event = type("Event", (), {
        "topic": "workspace.active",
        "payload": {"workspace_id": "ws-2", "title": "Active WS"},
        "source": "tests",
        "timestamp": 0.0,
    })()
    new_state = reduce_global_context_state(state, event)
    assert new_state.global_context.workspace_id == "ws-2"
    assert new_state.global_context.workspace_title == "Active WS"


def test_global_context_reducer_sets_active_goal_on_activation():
    """GOAL_ACTIVATED projects active goal into GlobalContextSnapshot."""
    state = _make_state()
    event = type("Event", (), {
        "topic": "goal.activated",
        "payload": {"goal": {"id": "g9", "text": "Close Phase B"}},
        "source": "tests",
        "timestamp": 0.0,
    })()
    new_state = reduce_global_context_state(state, event)
    assert new_state.global_context.active_goal_id == "g9"
    assert new_state.global_context.active_goal_title == "Close Phase B"
    assert new_state.global_context.revision == 1


def test_global_context_reducer_clears_active_goal_on_completion():
    """GOAL_COMPLETED clears the active goal when ids match."""
    state = _make_state(
        global_context=GlobalContextSnapshot(
            active_goal_id="g9",
            active_goal_title="Close Phase B",
            revision=2,
        ),
    )
    event = type("Event", (), {
        "topic": "goal.completed",
        "payload": {"goal_id": "g9"},
        "source": "tests",
        "timestamp": 0.0,
    })()
    new_state = reduce_global_context_state(state, event)
    assert new_state.global_context.active_goal_id == ""
    assert new_state.global_context.active_goal_title == ""
    assert new_state.global_context.revision == 3


def test_global_context_reducer_clears_on_ui_context_clear():
    """UI_CONTEXT_CLEAR resets entity/sources but preserves active goal."""
    state = _make_state(
        global_context=GlobalContextSnapshot(
            workspace_id="ws-3",
            entity_id="ent-1",
            active_goal_id="g1",
            active_goal_title="Keep me",
            sources=("note",),
            token_estimate=512,
            revision=5,
        ),
    )
    event = type("Event", (), {
        "topic": "ui.context.clear",
        "payload": {},
        "source": "tests",
        "timestamp": 0.0,
    })()
    new_state = reduce_global_context_state(state, event)
    assert new_state.global_context.entity_id == ""
    assert new_state.global_context.sources == ()
    assert new_state.global_context.token_estimate == 0
    assert new_state.global_context.active_goal_id == "g1"
    assert new_state.global_context.active_goal_title == "Keep me"
    assert new_state.global_context.revision == 6


def test_controller_publishes_context_select_and_clear():
    """UIController exposes global context select/clear intents."""
    bus = EventBus()
    store = type("Store", (), {"snapshot": AppState(), "subscribe": lambda self, cb: lambda: None})()
    controller = UIController(bus, store, lambda: None)

    seen: list[dict] = []
    bus.subscribe(UI_CONTEXT_SELECT, lambda e: seen.append(dict(e.payload)))
    bus.subscribe(UI_CONTEXT_CLEAR, lambda e: seen.append({"topic": e.topic}))

    controller.publish_context_select(
        "ent-1", entity_type="card", title="Card One", workspace_id="ws-1"
    )
    controller.publish_context_clear()

    assert len(seen) == 2
    assert seen[0]["entity_id"] == "ent-1"
    assert seen[0]["entity_type"] == "card"
    assert seen[0]["title"] == "Card One"
    assert seen[0]["workspace_id"] == "ws-1"
    assert seen[1] == {"topic": UI_CONTEXT_CLEAR}
