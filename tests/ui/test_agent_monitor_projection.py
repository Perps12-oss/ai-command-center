"""Projection tests for Phase 11D Agent Monitor workspace."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.core.app_state import AppState
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import AGENT_CANCEL_REQUEST
from ai_command_center.domain.agent_pipeline_snapshot import (
    AgentPipelineSnapshot,
    AgentRunSnapshot,
)
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.agent_monitor.active_agents_panel import sort_agent_runs
from ai_command_center.ui.views.agent_monitor.pipeline_progress_panel import (
    tool_progress_counts,
)
from tests.ui.fake_ui import AgentsView

ROOT = Path(__file__).resolve().parents[2]


def _sample_pipeline(*, active: bool = True) -> AgentPipelineSnapshot:
    runs = (
        AgentRunSnapshot(
            agent_id="research-1",
            request_id="req-r",
            state="running" if active else "terminated",
            task="demo: echo research",
            steps=2,
            workspace_id="ws-1",
            spawn_role="research",
        ),
        AgentRunSnapshot(
            agent_id="review-1",
            request_id="req-v",
            state="waiting",
            task="demo: echo review",
            steps=1,
            workspace_id="ws-1",
            spawn_role="review",
        ),
        AgentRunSnapshot(
            agent_id="failed-1",
            request_id="req-f",
            state="failed",
            task="demo: boom",
            error="tool failed",
            steps=1,
            workspace_id="ws-1",
            spawn_role="research",
        ),
        AgentRunSnapshot(
            agent_id="done-1",
            request_id="req-d",
            state="terminated",
            task="demo: done",
            steps=3,
            workspace_id="ws-1",
            spawn_role="review",
        ),
    )
    return AgentPipelineSnapshot(
        runs=runs,
        active_run_id="research-1" if active else "",
        active_run_ids=("research-1", "review-1") if active else (),
        pipeline_id="pipeline-abc123" if active else "",
        pipeline_stage="research" if active else "complete",
        planned_tools=("shell: echo research", "shell: echo review"),
        total_spawned=4,
    )


def _sample_snap(*, active: bool = True) -> AppState:
    return AppState(agent_pipeline=_sample_pipeline(active=active))


def test_hero_metrics_failure_count_and_pipeline() -> None:
    view = AgentsView(None)
    view.apply_state(_sample_snap(active=True))
    metrics = view._metrics.cget("text")
    assert "2 active" in metrics
    assert "stage research" in metrics
    assert "2 tools" in metrics
    assert "1 running" in metrics
    assert "1 failed" in metrics
    assert "Active Pipeline" in view._hero_hint.cget("text")
    assert view._hero_action.cget("state") == "normal"
    assert "Cancel Active Pipeline" in view._hero_action.cget("text")


def test_hero_cancel_disabled_when_idle() -> None:
    view = AgentsView(None)
    view.apply_state(_sample_snap(active=False))
    # Idle snap still has waiting/failed runs — waiting is active.
    # Build a fully idle projection.
    idle = AgentPipelineSnapshot(
        runs=(
            AgentRunSnapshot(agent_id="done-1", state="terminated", task="x", steps=1),
        ),
        pipeline_stage="complete",
    )
    view.apply_state(AppState(agent_pipeline=idle))
    assert view._hero_action.cget("state") == "disabled"


def test_active_agents_sort_order() -> None:
    runs = list(_sample_pipeline().runs)
    ordered = [r.state for r in sort_agent_runs(runs)]
    assert ordered == ["running", "waiting", "failed", "terminated"]


def test_pipeline_progress_stage_and_tool_counts() -> None:
    view = AgentsView(None)
    snap = _sample_snap(active=True)
    view.apply_state(snap)
    assert "research" in view._pipeline._stage.cget("text")
    planned, completed, remaining = tool_progress_counts(snap.agent_pipeline)
    assert planned == 2
    assert completed == 1  # terminated success
    assert remaining == 1
    counts = view._pipeline._counts.cget("text")
    assert "Planned 2" in counts
    assert "Completed 1" in counts
    assert "Remaining 1" in counts


def test_task_assignment_renders_selected() -> None:
    view = AgentsView(None)
    view.apply_state(_sample_snap())
    view._select("review-1")
    texts: list[str] = []
    for child in view._tasks._body.winfo_children():
        for nested in getattr(child, "winfo_children", lambda: [])():
            for leaf in getattr(nested, "winfo_children", lambda: [])():
                if hasattr(leaf, "cget"):
                    try:
                        texts.append(str(leaf.cget("text")))
                    except Exception:
                        pass
    assert any("demo: echo review" in t for t in texts)
    assert any("review" in t for t in texts)
    assert any("req-v" in t for t in texts)
    assert any("pipeline-abc123" in t for t in texts)


def test_history_renders_all_projected_runs_and_failures() -> None:
    view = AgentsView(None)
    pipeline = _sample_pipeline()
    view.apply_state(AppState(agent_pipeline=pipeline))
    assert view._history._count.cget("text") == "4"
    texts: list[str] = []
    for child in view._history._body.winfo_children():
        for nested in getattr(child, "winfo_children", lambda: [])():
            if hasattr(nested, "cget"):
                try:
                    texts.append(str(nested.cget("text")))
                except Exception:
                    pass
    joined = "\n".join(texts)
    assert "failed-1" in joined
    assert "tool failed" in joined
    assert "research-1" in joined
    assert "done-1" in joined


def test_agent_state_shows_error() -> None:
    view = AgentsView(None)
    view.apply_state(_sample_snap())
    view._select("failed-1")
    texts: list[str] = []
    for child in view._state._body.winfo_children():
        for nested in getattr(child, "winfo_children", lambda: [])():
            if hasattr(nested, "cget"):
                try:
                    texts.append(str(nested.cget("text")))
                except Exception:
                    pass
    assert any("failed" in t.lower() for t in texts)
    assert any("tool failed" in t for t in texts)


def test_cancel_publishes_agent_cancel_request() -> None:
    from ai_command_center.core.app_state import AppStateStore

    bus = EventBus()
    ctrl = UIController(bus, AppStateStore(bus), on_state=lambda: None)
    seen: list[dict] = []

    def _capture(event) -> None:
        seen.append(dict(event.payload))

    bus.subscribe(AGENT_CANCEL_REQUEST, _capture)
    ctrl.publish_agent_cancel_request("research-1", reason="cancel_active_pipeline")
    assert seen == [{"agent_id": "research-1", "reason": "cancel_active_pipeline"}]

    cancelled: list[tuple[str, str]] = []
    view = AgentsView(
        None,
        on_cancel=lambda aid, reason: cancelled.append((aid, reason)),
    )
    view.apply_state(_sample_snap(active=True))
    view._hero_action.invoke()
    assert cancelled == [("research-1", "cancel_active_pipeline")]


def test_contextual_cancel_selected_agent() -> None:
    cancelled: list[tuple[str, str]] = []
    # No active pipeline — selected active run drives cancel label.
    pipeline = AgentPipelineSnapshot(
        runs=(
            AgentRunSnapshot(
                agent_id="solo-1",
                request_id="r1",
                state="running",
                task="demo",
                steps=1,
                spawn_role="research",
            ),
        ),
        active_run_id="solo-1",
        active_run_ids=("solo-1",),
    )
    view = AgentsView(
        None,
        on_cancel=lambda aid, reason: cancelled.append((aid, reason)),
    )
    view.apply_state(AppState(agent_pipeline=pipeline))
    view._select("solo-1")
    assert "Selected Agent Run" in view._hero_action.cget("text")
    view._hero_action.invoke()
    assert cancelled == [("solo-1", "cancel_selected_agent_run")]


def test_agent_purple_token_used() -> None:
    files = [
        ROOT / "ai_command_center/ui/views/agents_view.py",
        ROOT / "ai_command_center/ui/views/agent_monitor/active_agents_panel.py",
        ROOT / "ai_command_center/ui/views/agent_monitor/agent_state_panel.py",
        ROOT / "ai_command_center/ui/views/agent_monitor/pipeline_progress_panel.py",
        ROOT / "ai_command_center/ui/views/agent_monitor/task_assignment_panel.py",
        ROOT / "ai_command_center/ui/views/agent_monitor/execution_history_panel.py",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "AGENT_PURPLE" in text, path.name
        assert "#9B59B6" not in text
    assert T.AGENT_PURPLE == "#9B59B6"


def test_no_repo_or_service_imports() -> None:
    files = [
        ROOT / "ai_command_center/ui/views/agents_view.py",
        ROOT / "ai_command_center/ui/views/agent_monitor/active_agents_panel.py",
        ROOT / "ai_command_center/ui/views/agent_monitor/pipeline_progress_panel.py",
        ROOT / "ai_command_center/ui/views/agent_monitor/execution_history_panel.py",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "ai_command_center.repositories" not in text
        assert "ai_command_center.services" not in text
        assert "add_listener" not in text
