"""Automation workspace AppState reducer tests."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    UI_AUTOMATION_SELECT,
    WORKFLOW_FAILED,
    WORKFLOW_STARTED,
)


def test_default_automation_workspace_has_catalog() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        snap = store.snapshot
        assert len(snap.automation_workspace.catalog) >= 1
        assert len(snap.automation_workspace.templates) >= 1
    finally:
        store.close()


def test_workflow_started_projects_active_runs() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            WORKFLOW_STARTED,
            {
                "run_id": "run-auto-1",
                "workflow_id": "demo-linear",
                "total_steps": 2,
                "steps": [
                    {"id": "a", "type": "tool", "tool": "shell"},
                    {"id": "b", "type": "tool", "tool": "shell"},
                ],
            },
            source="test",
        )
        snap = store.snapshot
        assert len(snap.automation_workspace.active_runs) == 1
        assert snap.automation_workspace.active_runs[0].run_id == "run-auto-1"
    finally:
        store.close()


def test_workflow_failed_projects_failure_queue() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            WORKFLOW_STARTED,
            {
                "run_id": "run-fail",
                "workflow_id": "demo-linear",
                "steps": [{"id": "a", "type": "tool", "tool": "shell"}],
            },
            source="test",
        )
        bus.publish(
            WORKFLOW_FAILED,
            {"run_id": "run-fail", "error": "tool step failed"},
            source="test",
        )
        snap = store.snapshot
        assert len(snap.automation_workspace.failures) == 1
        assert snap.automation_workspace.failures[0].error == "tool step failed"
    finally:
        store.close()


def test_automation_select_updates_selected_failure() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    try:
        bus.publish(
            UI_AUTOMATION_SELECT,
            {"run_id": "run-fail", "workflow_id": "demo-linear", "label": "Failed Run"},
            source="ui",
        )
        assert store.snapshot.automation_workspace.selected_failure_run_id == "run-fail"
    finally:
        store.close()
