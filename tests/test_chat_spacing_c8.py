"""C8: chat density — MSG_* tokens must drive outer-row spacing, not leftovers."""

from __future__ import annotations

import inspect

from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.chat.chat_view import ChatView
from ai_command_center.ui.views.chat import message_block


def test_msg_density_scale_is_tighter_than_pre_c8_wash() -> None:
    """Regression: first C8 pass kept 16/14/10 — density must actually shrink."""
    assert T.MSG_SIDE_PAD < 16
    assert T.MSG_BUBBLE_PAD_X < 14
    assert T.MSG_BUBBLE_PAD_Y < 10
    assert T.MSG_META_PAD_Y[1] < 6
    assert 0 < T.MSG_ROW_GAP <= 4
    assert T.MSG_BUBBLE_OUTER_PAD_Y == 0


def test_chat_view_outer_rows_use_msg_side_pad_and_row_gap() -> None:
    user_src = inspect.getsource(ChatView._user_row)
    asst_src = inspect.getsource(ChatView._assistant_row)
    strip_src = inspect.getsource(ChatView._add_strip)
    for src in (user_src, asst_src, strip_src):
        assert "MSG_SIDE_PAD" in src
        assert "MSG_ROW_GAP" in src
        assert "SIDE_PAD" not in src or "MSG_SIDE_PAD" in src
        assert "pady=(0, 8)" not in src
        assert "pady=(0, 4)" not in src


def test_message_block_uses_shared_inner_pads() -> None:
    src = inspect.getsource(message_block)
    assert "MSG_BUBBLE_PAD_X" in src
    assert "MSG_BUBBLE_PAD_Y" in src
    assert "MSG_META_PAD_Y" in src
    assert "MSG_BUBBLE_OUTER_PAD_Y" in src
    assert "MSG_INNER_PAD" in src
    assert "padx=14" not in src
    assert "pady=10" not in src
    assert "anchor=\"e\", pady=2)" not in src
    assert "anchor=\"w\", pady=2)" not in src
