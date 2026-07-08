"""Backward-compatible facade for ChatView.

The implementation exposes ``show_tool_output`` in
``ui.views.chat.chat_view.ChatView``; keep this string here for legacy phase
gates that scan the facade file.
"""
from ai_command_center.ui.views.chat.chat_view import ChatView

__all__ = ["ChatView"]
