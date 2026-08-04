"""Chat rail click bind + conversation list rebuild skip."""

from __future__ import annotations

import pytest

try:
    import tkinter as tk
except Exception as exc:  # pragma: no cover
    pytest.skip(f"tkinter unavailable: {exc}", allow_module_level=True)

try:
    _probe = tk.Tk()
    _probe.withdraw()
    _probe.destroy()
except Exception as exc:  # pragma: no cover
    pytest.skip(f"tkinter display unavailable: {exc}", allow_module_level=True)

import customtkinter as ctk

from ai_command_center.ui.views.chat.conversation_list import ConversationList
from ai_command_center.ui.views.chat.conversation_metadata import ConversationMetadata


@pytest.fixture
def root():
    app = ctk.CTk()
    app.withdraw()
    yield app
    try:
        app.destroy()
    except Exception:
        pass


def test_conversation_row_click_handler_tolerates_zero_args() -> None:
    """Regression: Tk/CTk may invoke bind callbacks without an Event (Py3.14)."""
    selected: list[str] = []

    def _on_click(*_args, sid: str = "s1") -> None:
        selected.append(sid)

    _on_click()
    _on_click(object())
    assert selected == ["s1", "s1"]


def test_set_conversations_skips_identical_rebuild(root) -> None:
    rebuilds = {"n": 0}
    original = ConversationList._rebuild_list

    def counted(self, *a, **k):  # noqa: ANN001
        rebuilds["n"] += 1
        return original(self, *a, **k)

    ConversationList._rebuild_list = counted  # type: ignore[method-assign]
    try:
        rail = ConversationList(
            root,
            on_new=lambda: None,
            on_select=lambda _s: None,
            on_delete=lambda _s: None,
        )
        items = [
            ConversationMetadata(session_id="a", title="A", last_activity=1.0),
            ConversationMetadata(session_id="b", title="B", last_activity=2.0),
        ]
        rail.set_conversations(items)
        assert rebuilds["n"] == 1
        rail.set_conversations(
            [
                ConversationMetadata(session_id="a", title="A", last_activity=1.0),
                ConversationMetadata(session_id="b", title="B", last_activity=2.0),
            ]
        )
        assert rebuilds["n"] == 1
        rail.set_conversations(
            [
                ConversationMetadata(session_id="a", title="A2", last_activity=1.0),
                ConversationMetadata(session_id="b", title="B", last_activity=2.0),
            ]
        )
        assert rebuilds["n"] == 2
    finally:
        ConversationList._rebuild_list = original  # type: ignore[method-assign]
