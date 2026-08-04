"""C7: assistant message height uses display lines + height cap with scrollbars."""

from __future__ import annotations

import pytest

try:
    import tkinter as tk
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter unavailable: {exc}", allow_module_level=True)

try:
    _probe = tk.Tk()
    _probe.withdraw()
    _probe.destroy()
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter display unavailable: {exc}", allow_module_level=True)

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.chat.message_block import AssistantMessageBlock


@pytest.fixture
def root():
    app = ctk.CTk()
    app.withdraw()
    yield app
    try:
        app.destroy()
    except Exception:
        pass


def test_resize_uses_displaylines_not_raw_newlines(root) -> None:
    block = AssistantMessageBlock(root)
    # One long line that wraps many times — newline count is 1.
    long = "word " * 400
    block.finalize(long)
    h = int(block._textbox.cget("height"))
    naive = 1 * T.MSG_TEXTBOX_LINE_PX + 10
    assert h > naive
    assert h <= T.MSG_TEXTBOX_MAX_H


def test_resize_caps_height_for_tall_content(root) -> None:
    block = AssistantMessageBlock(root)
    huge = "\n".join(["line"] * 80)
    block.finalize(huge)
    assert int(block._textbox.cget("height")) == T.MSG_TEXTBOX_MAX_H
    # Scrollbars were activated at construction so capped content stays reachable.
    assert bool(block._textbox.cget("activate_scrollbars")) is True
