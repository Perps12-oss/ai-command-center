"""C5/C6: New Chat creates a persisted conversation; prior history is preserved."""

from __future__ import annotations

import sqlite3

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CHAT_CONVERSATIONS_LOADED,
    CHAT_HISTORY_LOADED,
    UI_CHAT_NEW_SESSION,
    UI_CHAT_SELECT_CONVERSATION,
)
from ai_command_center.repositories.conversation_repository import ConversationRepository
from ai_command_center.repositories.database_bootstrap_repository import (
    DatabaseBootstrapRepository,
)
from ai_command_center.services.session_service import SessionService


def _svc() -> tuple[EventBus, ConversationRepository, SessionService]:
    bus = EventBus()
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    DatabaseBootstrapRepository().apply(conn)
    repo = ConversationRepository(conn)
    svc = SessionService(bus, repo)
    svc.load()
    return bus, repo, svc


def test_create_and_list_conversations() -> None:
    _bus, repo, svc = _svc()
    a = repo.create_conversation(title="New Chat")
    b = repo.create_conversation(title="New Chat")
    assert a != b
    repo.append_message("user", "hello from a", conversation_id=a)
    listed = repo.list_conversations()
    ids = {row["conversation_id"] for row in listed}
    assert a in ids and b in ids
    row_a = next(r for r in listed if r["conversation_id"] == a)
    assert row_a["title"] == "hello from a"
    assert row_a["message_count"] == 1
    svc.unload()


def test_new_session_creates_conversation_without_clearing_prior() -> None:
    bus, repo, svc = _svc()

    first = svc._active_conversation_id
    repo.append_message("user", "keep me", conversation_id=first)
    assert len(repo.list_messages(first)) == 1

    seen_history: list[dict] = []
    seen_list: list[dict] = []
    bus.subscribe(CHAT_HISTORY_LOADED, lambda e: seen_history.append(dict(e.payload)))
    bus.subscribe(CHAT_CONVERSATIONS_LOADED, lambda e: seen_list.append(dict(e.payload)))

    bus.publish(UI_CHAT_NEW_SESSION, {}, source="test")

    second = svc._active_conversation_id
    assert second != first
    assert len(repo.list_messages(first)) == 1
    assert repo.list_messages(second) == []
    assert seen_history and seen_history[-1]["conversation_id"] == second
    assert seen_history[-1]["messages"] == []
    assert any(
        second == c.get("conversation_id")
        for payload in seen_list
        for c in payload.get("conversations", [])
    )
    svc.unload()


def test_select_conversation_switches_active() -> None:
    bus, repo, svc = _svc()
    a = repo.create_conversation(title="A")
    repo.append_message("user", "alpha", conversation_id=a)
    bus.publish(UI_CHAT_NEW_SESSION, {}, source="test")
    b = svc._active_conversation_id
    assert b != a

    bus.publish(UI_CHAT_SELECT_CONVERSATION, {"conversation_id": a}, source="test")
    assert svc._active_conversation_id == a
    msgs = repo.list_messages(a)
    assert msgs and msgs[0].content == "alpha"
    svc.unload()
