"""Timeline undo handlers — dispatch TIMELINE_UNDO_REQUEST by undo_data.action."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import TIMELINE_UNDO_REQUEST, TIMELINE_UNDO_RESULT

# undo_data["action"] values — keep stable for persisted timeline rows
UNDO_DELETE_ENTITY = "delete_entity"
UNDO_DELETE_RELATIONSHIP = "delete_relationship"
UNDO_REMOVE_WORKSPACE_ENTITY = "remove_workspace_entity"


def _publish_undo_result(
    bus: Any,
    *,
    timeline_event_id: str,
    success: bool,
    action: str,
    detail: str = "",
    source: str,
) -> None:
    bus.publish(
        TIMELINE_UNDO_RESULT,
        {
            "timeline_event_id": timeline_event_id,
            "success": success,
            "action": action,
            "detail": detail,
        },
        source=source,
    )


def _handle_delete_entity(
    undo_data: dict[str, Any],
    *,
    entity_service: Any,
    bus: Any,
    timeline_event_id: str,
    source: str,
) -> bool:
    entity_id_raw = str(undo_data.get("entity_id") or "")
    if not entity_id_raw:
        _publish_undo_result(
            bus,
            timeline_event_id=timeline_event_id,
            success=False,
            action=UNDO_DELETE_ENTITY,
            detail="missing entity_id",
            source=source,
        )
        return False
    try:
        entity_id = UUID(entity_id_raw)
    except ValueError:
        _publish_undo_result(
            bus,
            timeline_event_id=timeline_event_id,
            success=False,
            action=UNDO_DELETE_ENTITY,
            detail="invalid entity_id",
            source=source,
        )
        return False
    deleted = entity_service.delete(entity_id)
    _publish_undo_result(
        bus,
        timeline_event_id=timeline_event_id,
        success=deleted,
        action=UNDO_DELETE_ENTITY,
        detail="" if deleted else "entity not found",
        source=source,
    )
    return deleted


def _handle_delete_relationship(
    undo_data: dict[str, Any],
    *,
    relationship_service: Any,
    bus: Any,
    timeline_event_id: str,
    source: str,
) -> bool:
    relationship_id_raw = str(undo_data.get("relationship_id") or "")
    if not relationship_id_raw:
        _publish_undo_result(
            bus,
            timeline_event_id=timeline_event_id,
            success=False,
            action=UNDO_DELETE_RELATIONSHIP,
            detail="missing relationship_id",
            source=source,
        )
        return False
    try:
        relationship_id = UUID(relationship_id_raw)
    except ValueError:
        _publish_undo_result(
            bus,
            timeline_event_id=timeline_event_id,
            success=False,
            action=UNDO_DELETE_RELATIONSHIP,
            detail="invalid relationship_id",
            source=source,
        )
        return False
    deleted = relationship_service.delete(relationship_id)
    _publish_undo_result(
        bus,
        timeline_event_id=timeline_event_id,
        success=deleted,
        action=UNDO_DELETE_RELATIONSHIP,
        detail="" if deleted else "relationship not found",
        source=source,
    )
    return deleted


def _handle_remove_workspace_entity(
    undo_data: dict[str, Any],
    *,
    workspace_service: Any,
    bus: Any,
    timeline_event_id: str,
    source: str,
) -> bool:
    workspace_id_raw = str(undo_data.get("workspace_id") or "")
    entity_id_raw = str(undo_data.get("entity_id") or "")
    if not workspace_id_raw or not entity_id_raw:
        _publish_undo_result(
            bus,
            timeline_event_id=timeline_event_id,
            success=False,
            action=UNDO_REMOVE_WORKSPACE_ENTITY,
            detail="missing workspace_id or entity_id",
            source=source,
        )
        return False
    try:
        workspace_id = UUID(workspace_id_raw)
        entity_id = UUID(entity_id_raw)
    except ValueError:
        _publish_undo_result(
            bus,
            timeline_event_id=timeline_event_id,
            success=False,
            action=UNDO_REMOVE_WORKSPACE_ENTITY,
            detail="invalid workspace_id or entity_id",
            source=source,
        )
        return False
    before = workspace_service.get(workspace_id)
    if before is None:
        _publish_undo_result(
            bus,
            timeline_event_id=timeline_event_id,
            success=False,
            action=UNDO_REMOVE_WORKSPACE_ENTITY,
            detail="workspace not found",
            source=source,
        )
        return False
    workspace_service.remove_entity(workspace_id, entity_id)
    _publish_undo_result(
        bus,
        timeline_event_id=timeline_event_id,
        success=True,
        action=UNDO_REMOVE_WORKSPACE_ENTITY,
        source=source,
    )
    return True



def register_timeline_undo_handlers(
    bus: Any,
    *,
    entity_service: Any,
    relationship_service: Any,
    workspace_service: Any,
    source: str = "timeline_undo_handlers",
) -> list[Callable[[], None]]:
    """Wire TIMELINE_UNDO_REQUEST dispatch. Returns unsubscribe callbacks."""

    def on_timeline_undo_request(event: Event) -> None:
        payload = dict(event.payload or {})
        timeline_event_id = str(payload.get("timeline_event_id") or "")
        undo_data = dict(payload.get("undo_data") or {})
        action = str(undo_data.get("action") or "")
        if not action:
            _publish_undo_result(
                bus,
                timeline_event_id=timeline_event_id,
                success=False,
                action="",
                detail="missing undo action",
                source=source,
            )
            return
        if action == UNDO_DELETE_ENTITY:
            _handle_delete_entity(
                undo_data,
                entity_service=entity_service,
                bus=bus,
                timeline_event_id=timeline_event_id,
                source=source,
            )
        elif action == UNDO_DELETE_RELATIONSHIP:
            _handle_delete_relationship(
                undo_data,
                relationship_service=relationship_service,
                bus=bus,
                timeline_event_id=timeline_event_id,
                source=source,
            )
        elif action == UNDO_REMOVE_WORKSPACE_ENTITY:
            _handle_remove_workspace_entity(
                undo_data,
                workspace_service=workspace_service,
                bus=bus,
                timeline_event_id=timeline_event_id,
                source=source,
            )
        else:
            _publish_undo_result(
                bus,
                timeline_event_id=timeline_event_id,
                success=False,
                action=action,
                detail=f"unsupported undo action: {action}",
                source=source,
            )

    return [bus.subscribe(TIMELINE_UNDO_REQUEST, on_timeline_undo_request)]


__all__ = [
    "UNDO_DELETE_ENTITY",
    "UNDO_DELETE_RELATIONSHIP",
    "UNDO_REMOVE_WORKSPACE_ENTITY",
    "register_timeline_undo_handlers",
]
