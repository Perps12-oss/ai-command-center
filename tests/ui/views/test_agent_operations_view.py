"""UI tests for PR-UI-E09 Agent Operations Center."""

from __future__ import annotations

from ai_command_center.core.app_state import AppState, AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import UI_AGENT_OPEN, UI_AGENT_SELECT
from ai_command_center.domain.agent_pipeline_snapshot import (
    AgentPipelineSnapshot,
    AgentRunSnapshot,
)
from ai_command_center.ui.components.agent.run_timeline import planned_tool_steps
from ai_command_center.ui.controller import UIController
from tests.ui.fake_ui import AgentCard, AgentsView, PipelineStage, RunTimeline


def _pipeline() -> AgentPipelineSnapshot:
    return AgentPipelineSnapshot(
        runs=(
            AgentRunSnapshot(
                agent_id="research-1",
                state="running",
                task="ship E09",
                steps=2,
                spawn_role="research",
            ),
            AgentRunSnapshot(
                agent_id="review-1",
                state="waiting",
                task="review",
                steps=1,
                spawn_role="review",
            ),
        ),
        active_run_id="research-1",
        active_run_ids=("research-1", "review-1"),
        pipeline_id="pipe-1",
        pipeline_stage="research",
        planned_tools=("shell: echo", "shell: review"),
        total_spawned=2,
    )


def test_agent_operations_projects_runs_stage_tools():
    inspected: list[object] = []
    view = AgentsView(None, on_inspect_select=lambda ref: inspected.append(ref))
    view.apply_state(AppState(agent_pipeline=_pipeline()))
    metrics = view._metrics.cget("text")
    assert "2 active" in metrics
    assert "stage research" in metrics
    assert "2 tools" in metrics
    assert "stage: research" in view._stage._stage.cget("text")
    assert len(view._cards_scroll.winfo_children()) >= 2

    view._select("research-1")
    assert view._selected_agent_id == "research-1"
    assert inspected and getattr(inspected[-1], "kind") == "agent"
    payload = dict(getattr(inspected[-1], "payload"))
    assert payload.get("task") == "ship E09"
    assert payload.get("role") == "research"


def test_agent_components_and_timeline_helper():
    selected: list[str] = []
    AgentCard(
        None,
        agent_id="a1",
        role="research",
        state="running",
        on_select=lambda aid: selected.append(aid),
    )._click()
    assert selected == ["a1"]

    pipe = _pipeline()
    stage = PipelineStage(None)
    stage.apply_snapshot(pipe)
    assert "research" in stage._stage.cget("text")

    timeline = RunTimeline(None)
    timeline.apply_snapshot(pipe, selected_agent_id="research-1")
    steps = planned_tool_steps(pipe)
    assert len(steps) == 2
    assert steps[0]["name"] == "shell: echo"


def test_controller_agent_intents():
    bus = EventBus()
    store = AppStateStore(bus)
    controller = UIController(bus, store, lambda: None)
    seen: list[str] = []
    bus.subscribe(UI_AGENT_SELECT, lambda e: seen.append(e.topic))
    bus.subscribe(UI_AGENT_OPEN, lambda e: seen.append(e.topic))
    controller.publish_agent_select("research-1")
    controller.publish_agent_open()
    assert seen == [UI_AGENT_SELECT, UI_AGENT_OPEN]
