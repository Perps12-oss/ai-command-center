"""In-memory session and message history state."""
from __future__ import annotations

import time
import uuid
from typing import Callable


def new_sid() -> str:
    return uuid.uuid4().hex[:8]


def hhmm() -> str:
    return time.strftime("%H:%M")


def session_title(history: list[dict]) -> str | None:
    """Derive a display title from the first user message, if any."""
    if not history:
        return None
    first_user = next(
        (m["content"] for m in history if m.get("role") == "user"), None
    )
    if not first_user:
        return None
    return (first_user[:36] + "…") if len(first_user) > 36 else first_user


class SessionStore:
    """Owns in-memory chat sessions and the active conversation history."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[dict]] = {}
        self._session_id: str = new_sid()
        self._history: list[dict] = []

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def history(self) -> list[dict]:
        return self._history

    @property
    def sessions(self) -> dict[str, list[dict]]:
        return self._sessions

    def set_history(self, messages: list[dict]) -> None:
        self._history = list(messages)

    def append_message(self, role: str, content: str) -> None:
        self._history.append({"role": role, "content": content})

    def clear_history(self) -> None:
        self._history = []

    def start_new_session(self) -> str:
        """Return the new session id after rotating away from the current one."""
        self._session_id = new_sid()
        self._history = []
        return self._session_id

    def load_session(self, sid: str) -> list[dict]:
        """Switch active session and return its messages."""
        self._session_id = sid
        messages = list(self._sessions.get(sid, []))
        self._history = messages
        return messages

    def delete_session(self, sid: str) -> bool:
        """Remove a session. Returns True if it was the active session."""
        was_active = sid == self._session_id
        self._sessions.pop(sid, None)
        return was_active

    def save_current_session(
        self,
        *,
        on_update: Callable[[str, str, str], None],
        on_add: Callable[[str, str, str], None],
    ) -> None:
        """Save current conversation into the session store."""
        title = session_title(self._history)
        if title is None:
            return
        sid = self._session_id
        existed = sid in self._sessions
        self._sessions[sid] = list(self._history)
        timestamp = hhmm()
        if existed:
            on_update(sid, title, timestamp)
        else:
            on_add(sid, title, timestamp)
