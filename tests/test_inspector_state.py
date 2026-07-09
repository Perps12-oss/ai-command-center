from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.events.topics import (
    UI_INSPECT_CLEAR,
    UI_INSPECT_NAVIGATE,
    UI_INSPECT_SELECT,
)
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.controller import UIController


def test_inspectable_ref_helper_from_payload() -> None:
    ref = InspectableRef.from_payload(
        {
            "kind": "message",
            "ref_id": "msg-1",
            "label": "Hello",
            "payload": {
                "role": "user",
                "content": "Hi there",
                "tokens": 12,
            },
        }
    )

    assert ref.kind == "message"
    assert ref.ref_id == "msg-1"
    assert ref.label == "Hello"
    assert ref.payload == (("role", "user"), ("content", "Hi there"), ("tokens", "12"))
    assert ref.as_dict() == {"role": "user", "content": "Hi there", "tokens": "12"}
    assert ref.get("content") == "Hi there"
    assert ref.get("missing", "fallback") == "fallback"

    with pytest.raises(FrozenInstanceError):
        ref.ref_id = "mutated"  # type: ignore[misc]


def test_inspector_select_and_clear_projection(event_bus) -> None:
    store = AppStateStore(event_bus)

    event_bus.publish(
        UI_INSPECT_SELECT,
        {
            "kind": "message",
            "ref_id": "msg-1",
            "label": "Hi",
            "payload": {"role": "user", "content": "Hello"},
        },
        source="tests",
    )
    snap = store.snapshot
    assert snap.inspector.selected is not None
    assert snap.inspector.selected.kind == "message"
    assert snap.inspector.selected.ref_id == "msg-1"
    assert snap.inspector.revision == 1

    event_bus.publish(
        UI_INSPECT_SELECT,
        {
            "kind": "message",
            "ref_id": "msg-1",
            "label": "Hi",
            "payload": {"role": "user", "content": "Hello"},
        },
        source="tests",
    )
    assert store.snapshot.inspector.revision == 1

    before = snap.inspector
    event_bus.publish(UI_INSPECT_CLEAR, {}, source="tests")
    after = store.snapshot.inspector
    assert after.selected is None
    assert after.revision == 2
    assert after is not before


def test_inspector_navigate_projects_target_without_changing_selection(event_bus) -> None:
    store = AppStateStore(event_bus)

    event_bus.publish(
        UI_INSPECT_SELECT,
        {"kind": "message", "ref_id": "msg-1", "payload": {"role": "user"}},
        source="tests",
    )
    before = store.snapshot.inspector
    event_bus.publish(
        UI_INSPECT_NAVIGATE,
        {"kind": "artifact", "ref_id": "art-1", "label": "Artifact One"},
        source="tests",
    )
    after = store.snapshot.inspector

    assert after.selected == before.selected
    assert after.revision == before.revision
    assert after.navigate_target is not None
    assert after.navigate_target.kind == "artifact"
    assert after.navigate_target.ref_id == "art-1"
    assert after.navigate_revision == 1


def test_resolve_inspect_navigate_view_maps_known_kinds() -> None:
    from ai_command_center.core.state.inspector_state import resolve_inspect_navigate_view

    assert resolve_inspect_navigate_view("message") == "chat"
    assert resolve_inspect_navigate_view("artifact") == "artifacts"
    assert resolve_inspect_navigate_view("provider") == "providers"
    assert resolve_inspect_navigate_view("execution") == "executions"
    assert resolve_inspect_navigate_view("decision") == "chat"
    assert resolve_inspect_navigate_view("unknown") is None


def test_empty_payload_noop(event_bus) -> None:
    store = AppStateStore(event_bus)

    event_bus.publish(UI_INSPECT_SELECT, {"kind": "", "ref_id": ""}, source="tests")
    event_bus.publish(UI_INSPECT_SELECT, {"kind": "message"}, source="tests")

    snap = store.snapshot
    assert snap.inspector.selected is None
    assert snap.inspector.revision == 0


def test_controller_publish_methods(event_bus) -> None:
    store = AppStateStore(event_bus)
    controller = UIController(event_bus, store, lambda: None)

    controller.publish_inspect_select(
        "message",
        "msg-7",
        label="Greeting",
        payload={"role": "assistant", "content": "Hello"},
    )
    controller.publish_inspect_navigate("message", "msg-7")
    controller.publish_inspect_clear()

    topics = [event.topic for event in event_bus.recorded[-3:]]
    assert topics == [UI_INSPECT_SELECT, UI_INSPECT_NAVIGATE, UI_INSPECT_CLEAR]

    select_event = event_bus.recorded[-3]
    assert select_event.payload["kind"] == "message"
    assert select_event.payload["ref_id"] == "msg-7"
    assert select_event.payload["label"] == "Greeting"
    assert select_event.payload["payload"] == {"role": "assistant", "content": "Hello"}
    assert select_event.source == "ui"
