"""Devin PR #26 cleanup — permission payload and workspace lifecycle."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.core.app_state import AppStateStore, _is_pending_chat_user_text
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
    PERMISSION_CHECK_REQUEST,
    PERMISSION_CHECK_RESULT,
)
from ai_command_center.core.permission.permission_service import PermissionService
from ai_command_center.core.service_factory import build_services
from ai_command_center.db.connection import connect, init_database


def test_agent_command_not_pending_chat_user_text() -> None:
    assert _is_pending_chat_user_text("agent: demo") is False
    assert _is_pending_chat_user_text("hello world") is True


def test_command_routed_agent_command_clears_pending_user_text() -> None:
    bus = EventBus()
    store = AppStateStore(bus)
    bus.publish(COMMAND_ROUTED, {"text": "agent: demo", "intent": "agent"}, source="test")
    assert store.snapshot.chat_pending_user_text == ""
    store.close()


def test_permission_check_request_omits_none_entity_type() -> None:
    bus = EventBus()
    permission = PermissionService(bus)
    permission.wire_bus_handlers()
    results: list[dict] = []
    bus.subscribe("permission.check", lambda e: results.append(dict(e.payload)))
    bus.publish(
        PERMISSION_CHECK_REQUEST,
        {"check_id": "c1", "permissions": ["launch_tool"], "actor_type": "agent"},
        source="test",
    )
    assert results and "entity_type" not in results[0]


def test_workspace_os_unload_does_not_unwire_permission_handlers() -> None:
    db = init_database(connect(Path(":memory:")))
    bus = EventBus()
    wired = build_services(db, bus, workspace_os_enabled=True)
    wired.services.load_all()
    wired.workspace_os.stop()
    results: list[dict] = []
    bus.subscribe(PERMISSION_CHECK_RESULT, lambda e: results.append(dict(e.payload)))
    bus.publish(
        PERMISSION_CHECK_REQUEST,
        {"check_id": "still-wired", "permissions": ["read_entity"], "actor_type": "user"},
        source="test",
    )
    assert results and results[0]["granted"] is True
    wired.services.shutdown()
    db.close()
