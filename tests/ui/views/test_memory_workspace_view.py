"""UI tests for PR-UI-E05 Memory Workspace."""

from __future__ import annotations

import pytest

from ai_command_center.core.app_state import AppState, MemoryItem
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    UI_MEMORY_CLEAR,
    UI_MEMORY_SEARCH,
    UI_MEMORY_SELECT,
)
from ai_command_center.core.state.global_context_state import GlobalContextSnapshot
from ai_command_center.domain.notes_memory_snapshot import (
    MemoryCatalogItem,
    NotesMemorySnapshot,
)
from ai_command_center.ui.controller import UIController
from tests.ui.fake_ui import MemoryCard, MemoryDetail, MemoryView


@pytest.fixture
def memory_view():
    return MemoryView(
        None,
        on_delete=lambda _id, _text: None,
        on_add=lambda _label, _content: None,
    )


def test_memory_view_loads_catalog_and_search(memory_view):
    snap = AppState(
        memory_catalog=(
            MemoryItem(node_id="m1", label="alpha fact"),
            MemoryItem(node_id="m2", label="beta note"),
        ),
        notes_memory=NotesMemorySnapshot(
            memory_catalog=(
                MemoryCatalogItem(node_id="m1", label="alpha fact"),
                MemoryCatalogItem(node_id="m2", label="beta note"),
            )
        ),
    )
    memory_view.load_from_appstate(snap)
    assert len(memory_view._items) == 2

    memory_view._search.configure(text="beta")
    # Fake entry uses kwargs; set via internal API used by get()
    memory_view._search._kwargs["text"] = "beta"
    visible = memory_view._visible_items()
    assert len(visible) == 1
    assert visible[0]["label"] == "beta note"


def test_memory_view_select_updates_detail_and_inspect():
    seen_select: list[dict] = []
    seen_inspect: list[object] = []

    view = MemoryView(
        None,
        on_delete=lambda _i, _t: None,
        on_select=lambda item: seen_select.append(item),
        on_inspect_select=lambda ref: seen_inspect.append(ref),
    )
    view.load_memories(
        [{"id": "m9", "label": "selected", "text": "selected", "content": "body"}]
    )
    view._handle_select(view._items[0])
    assert seen_select and seen_select[0]["id"] == "m9"
    assert seen_inspect and getattr(seen_inspect[0], "kind") == "memory"
    assert "selected" in view._detail._title.cget("text")


def test_injection_indicator_marks_context_overlap(memory_view):
    snap = AppState(
        memory_catalog=(MemoryItem(node_id="m1", label="injected-one"),),
        memory_selected=("injected-one",),
        notes_memory=NotesMemorySnapshot(
            memory_catalog=(MemoryCatalogItem(node_id="m1", label="injected-one"),),
            memory_selected=("injected-one",),
        ),
        global_context=GlobalContextSnapshot(sources=("injected-one", "note-x")),
    )
    memory_view.load_from_appstate(snap)
    assert memory_view._is_injected(memory_view._items[0])


def test_memory_card_and_detail_components():
    selected: list[dict] = []
    card = MemoryCard(
        None,
        item={"id": "1", "label": "L", "text": "L"},
        selected=True,
        injected=True,
        on_select=lambda item: selected.append(item),
    )
    card._handle_select()
    assert selected[0]["id"] == "1"

    detail = MemoryDetail(None)
    detail.show({"id": "1", "label": "L", "content": "body"}, injected=True)
    assert "L" in detail._title.cget("text")


def test_controller_publishes_ui_memory_intents():
    bus = EventBus()
    from ai_command_center.core.app_state import AppStateStore

    store = AppStateStore(bus)
    controller = UIController(bus, store, lambda: None)
    seen: list[tuple[str, dict]] = []
    bus.subscribe(UI_MEMORY_SELECT, lambda e: seen.append((e.topic, dict(e.payload))))
    bus.subscribe(UI_MEMORY_CLEAR, lambda e: seen.append((e.topic, dict(e.payload))))
    bus.subscribe(UI_MEMORY_SEARCH, lambda e: seen.append((e.topic, dict(e.payload))))

    controller.publish_memory_select("m1", label="L", workspace_id="ws")
    controller.publish_memory_clear()
    controller.publish_memory_search("query")

    assert seen[0][0] == UI_MEMORY_SELECT
    assert seen[0][1]["memory_id"] == "m1"
    assert seen[1][0] == UI_MEMORY_CLEAR
    assert seen[2][1]["query"] == "query"
