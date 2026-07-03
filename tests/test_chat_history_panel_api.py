"""ChatHistoryPanel exposes update_session for session save flow."""

from __future__ import annotations

import inspect

from ai_command_center.ui.components.chat_history_panel import ChatHistoryPanel


def test_chat_history_panel_exposes_update_session() -> None:
    assert hasattr(ChatHistoryPanel, "update_session")
    sig = inspect.signature(ChatHistoryPanel.update_session)
    params = list(sig.parameters)
    assert params == ["self", "sid", "title", "ts"]
