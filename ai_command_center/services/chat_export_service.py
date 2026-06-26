"""Chat export service — writes chat history to markdown from EventBus request.

UI isolation: the UI never writes files; it publishes CHAT_EXPORT_REQUEST.
This service handles the filesystem write and publishes result/error events.
"""

from __future__ import annotations

import pathlib
import time
from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CHAT_EXPORT_ERROR,
    CHAT_EXPORT_REQUEST,
    CHAT_EXPORT_RESULT,
)
from ai_command_center.services.base import BaseService


class ChatExportService(BaseService):
    name = "chat_export"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsub: Callable[[], None] | None = None

    def _on_load(self) -> None:
        self._unsub = self._bus.subscribe(CHAT_EXPORT_REQUEST, self._on_export_request)

    def _on_unload(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    def _on_export_request(self, event: Event) -> None:
        history = event.payload.get("history") or []
        ts = time.strftime("%Y%m%d-%H%M%S")
        path = pathlib.Path.home() / f"chat_export_{ts}.md"
        lines = [f"# Chat Export — {ts}\n"]
        for msg in history:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role", "unknown")).capitalize()
            content = str(msg.get("content", "")).strip()
            if not content:
                continue
            lines.append(f"## {role}\n\n{content}\n")
        try:
            path.write_text("\n".join(lines), encoding="utf-8")
            self._bus.publish(
                CHAT_EXPORT_RESULT,
                {"path": str(path), "name": path.name},
                source=self.name,
            )
        except Exception as exc:
            self._bus.publish(
                CHAT_EXPORT_ERROR,
                {"message": str(exc)},
                source=self.name,
            )
