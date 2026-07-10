"""Bus request/result handlers for Workspace OS entity operations (Program 3 W3).

Registered from ``service_factory`` at composition root. Handlers run synchronously
on the caller thread so orchestrators can read ``pending[request_id]`` inline.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from ai_command_center.core.entity.entity import (
    ENTITY_TYPE_CARD,
    ENTITY_TYPE_RESOURCE,
    ENTITY_TYPE_WORKSPACE,
    RESOURCE_TYPE_COMMAND,
    RESOURCE_TYPE_FOLDER,
    RESOURCE_TYPE_URL,
)
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    ACTION_INVOKE_REQUEST,
    ACTION_INVOKE_RESULT,
    ENTITY_CONTEXT_REQUEST,
    ENTITY_CONTEXT_RESULT,
    ENTITY_CREATE_REQUEST,
    ENTITY_CREATE_RESULT,
    ENTITY_SEARCH_REQUEST,
    ENTITY_SEARCH_RESULT,
    RELATIONSHIP_CREATE_REQUEST,
    RELATIONSHIP_CREATE_RESULT,
    TIMELINE_RECORD_REQUEST,
    TIMELINE_RECORD_RESULT,
    SERVICE_READY,
    UI_SELECT_ENTITY,
    UI_SELECT_WORKSPACE,
    WORKSPACE_ADD_ENTITY_REQUEST,
    WORKSPACE_ADD_ENTITY_RESULT,
    WORKSPACE_CONTEXT_REQUEST,
    WORKSPACE_CONTEXT_RESULT,
    WORKSPACE_CREATE_REQUEST,
    WORKSPACE_CREATE_RESULT,
)
from ai_command_center.core.relationship.relationship import RelationshipType
<<<<<<< HEAD
from ai_command_center.core.timeline.timeline_undo_handlers import (
    UNDO_DELETE_ENTITY,
    UNDO_DELETE_RELATIONSHIP,
    UNDO_REMOVE_WORKSPACE_ENTITY,
)


def _record_reversible_timeline(
    timeline_service: Any,
    *,
    event_type: str,
    entity_id: UUID | None,
    entity_type: str | None,
    payload: dict[str, object],
    undo_data: dict[str, object],
) -> None:
    timeline_service.record(
        event_type=event_type,
        entity_id=entity_id,
        entity_type=entity_type,
        payload=payload,
        reversible=True,
        undo_data=undo_data,
    )
=======
from ai_command_center.core.world_model.context_compiler import (
    EntityLine,
    RelationshipLine,
    compile_entity_focus,
    compile_workspace_snapshot,
)
>>>>>>> origin/main


def _request_id(event: Event) -> str:
    return str(event.payload.get("request_id", ""))


def _publish_result(
    bus: Any,
    topic: str,
    request_id: str,
    payload: dict[str, object],
    *,
    source: str,
) -> None:
    if not request_id:
        return
    bus.publish(topic, {"request_id": request_id, **payload}, source=source)


def _resolve_parent_workspace_id(
    entity_service: Any,
    relationship_service: Any,
    entity_id: UUID,
    entity_type: str,
) -> UUID | None:
    """Resolve the parent workspace for a canvas entity (card, resource, note)."""
    if entity_type == ENTITY_TYPE_WORKSPACE:
        return entity_id
    entity = entity_service.get(entity_id)
    if entity is not None:
        meta = dict(entity.metadata)
        ws_raw = str(meta.get("workspace_id", "")).strip()
        if ws_raw:
            try:
                return UUID(ws_raw)
            except ValueError:
                pass
        card_raw = str(meta.get("card_id", "")).strip()
        if card_raw:
            try:
                card_id = UUID(card_raw)
            except ValueError:
                card_id = None
            if card_id is not None:
                parent = _resolve_parent_workspace_id(
                    entity_service,
                    relationship_service,
                    card_id,
                    ENTITY_TYPE_CARD,
                )
                if parent is not None:
                    return parent
    if entity_type == ENTITY_TYPE_CARD:
        for workspace in entity_service.get_by_type(ENTITY_TYPE_WORKSPACE):
            child_ids = [
                UUID(str(child))
                for child in workspace.metadata.get("entities", [])
            ]
            if entity_id in child_ids:
                return workspace.id
    if entity_type == ENTITY_TYPE_RESOURCE:
        for rel in relationship_service.get_by_target(entity_id):
            if rel.relationship_type == RelationshipType.CONTAINS:
                parent = _resolve_parent_workspace_id(
                    entity_service,
                    relationship_service,
                    rel.source_id,
                    ENTITY_TYPE_CARD,
                )
                if parent is not None:
                    return parent
    return None


def register_entity_bus_handlers(
    bus: Any,
    *,
    entity_service: Any,
    relationship_service: Any,
    workspace_service: Any,
    timeline_service: Any,
    action_registry: Any,
    source: str = "entity_bus_handlers",
) -> list[Callable[[], None]]:
    """Wire synchronous entity/workspace bus handlers. Returns unsubscribe callbacks."""

    def on_entity_create_request(event: Event) -> None:
        rid = _request_id(event)
        payload = event.payload
        try:
            entity = entity_service.create(
                entity_type=str(payload["entity_type"]),
                title=str(payload["title"]),
                description=str(payload.get("description", "")),
                metadata=dict(payload.get("metadata") or {}),
            )
            _publish_result(
                bus,
                ENTITY_CREATE_RESULT,
                rid,
                {
                    "entity_id": str(entity.id),
                    "entity_type": entity.entity_type,
                    "title": entity.title,
                    "metadata": dict(entity.metadata),
                },
                source=source,
            )
            _record_reversible_timeline(
                timeline_service,
                event_type="entity.created",
                entity_id=entity.id,
                entity_type=entity.entity_type,
                payload={
                    "title": entity.title,
                    "entity_type": entity.entity_type,
                },
                undo_data={
                    "action": UNDO_DELETE_ENTITY,
                    "entity_id": str(entity.id),
                },
            )
        except Exception as exc:  # noqa: BLE001 — bus handler surfaces error to caller
            _publish_result(
                bus,
                ENTITY_CREATE_RESULT,
                rid,
                {"error": str(exc)},
                source=source,
            )

    def on_entity_search_request(event: Event) -> None:
        rid = _request_id(event)
        query = str(event.payload.get("query", ""))
        entity_type = event.payload.get("entity_type")
        et = str(entity_type) if entity_type else None
        try:
            results = entity_service.search(query, entity_type=et)
            _publish_result(
                bus,
                ENTITY_SEARCH_RESULT,
                rid,
                {
                    "query": query,
                    "count": len(results),
                    "entity_ids": [str(e.id) for e in results],
                },
                source=source,
            )
        except Exception as exc:  # noqa: BLE001
            _publish_result(
                bus,
                ENTITY_SEARCH_RESULT,
                rid,
                {"query": query, "count": 0, "entity_ids": [], "error": str(exc)},
                source=source,
            )

    def on_entity_context_request(event: Event) -> None:
        rid = _request_id(event)
        entity_id_raw = str(event.payload.get("entity_id", "")).strip()
        if not entity_id_raw:
            _publish_result(
                bus,
                ENTITY_CONTEXT_RESULT,
                rid,
                {"snippets": []},
                source=source,
            )
            return

        try:
            entity_uuid = UUID(entity_id_raw)
        except ValueError:
            _publish_result(
                bus,
                ENTITY_CONTEXT_RESULT,
                rid,
                {"snippets": [], "error": "invalid entity_id"},
                source=source,
            )
            return

        entity = entity_service.get(entity_uuid)
        if entity is None:
            _publish_result(
                bus,
                ENTITY_CONTEXT_RESULT,
                rid,
                {"snippets": []},
                source=source,
            )
            return

        outgoing_edges: list[RelationshipLine] = []
        for rel in relationship_service.get_by_source(entity_uuid):
            target = entity_service.get(rel.target_id)
            if target is not None:
                outgoing_edges.append(
                    RelationshipLine(
                        predicate=rel.relationship_type.value,
                        target_type=target.entity_type,
                        target_title=target.title,
                        target_id=str(target.id),
                    )
                )
        incoming_edges: list[RelationshipLine] = []
        for rel in relationship_service.get_by_target(entity_uuid):
            source_entity = entity_service.get(rel.source_id)
            if source_entity is not None:
                incoming_edges.append(
                    RelationshipLine(
                        predicate=rel.relationship_type.value,
                        target_type=source_entity.entity_type,
                        target_title=source_entity.title,
                        target_id=str(source_entity.id),
                        direction="incoming",
                    )
                )

        resource_fields: dict[str, str] = {}
        if entity.entity_type == ENTITY_TYPE_RESOURCE:
            meta = dict(entity.metadata)
            resource_fields["resource_type"] = str(meta.get("resource_type", ""))
            for key in ("url", "path", "command", "plugin_id"):
                if meta.get(key):
                    resource_fields[key] = str(meta[key])

        compiled = compile_entity_focus(
            entity_id=str(entity.id),
            entity_type=entity.entity_type,
            entity_title=entity.title,
            entity_description=entity.description,
            resource_fields=resource_fields or None,
            outgoing_edges=outgoing_edges or None,
            incoming_edges=incoming_edges or None,
        )
        snippets: list[str] = [compiled] if compiled else []

        _publish_result(
            bus,
            ENTITY_CONTEXT_RESULT,
            rid,
            {"snippets": snippets},
            source=source,
        )

    def on_workspace_context_request(event: Event) -> None:
        rid = _request_id(event)
        workspace_id_raw = str(event.payload.get("workspace_id", "")).strip()
        focus_entity_raw = str(event.payload.get("entity_id", "")).strip()
        max_depth = int(event.payload.get("max_depth", 2) or 2)
        if not workspace_id_raw:
            _publish_result(
                bus,
                WORKSPACE_CONTEXT_RESULT,
                rid,
                {"snippets": []},
                source=source,
            )
            return
        try:
            workspace_uuid = UUID(workspace_id_raw)
        except ValueError:
            _publish_result(
                bus,
                WORKSPACE_CONTEXT_RESULT,
                rid,
                {"snippets": [], "error": "invalid workspace_id"},
                source=source,
            )
            return

        workspace = entity_service.get(workspace_uuid)
        if workspace is None or workspace.entity_type != ENTITY_TYPE_WORKSPACE:
            _publish_result(
                bus,
                WORKSPACE_CONTEXT_RESULT,
                rid,
                {"snippets": []},
                source=source,
            )
            return

        child_ids_raw = workspace.metadata.get("entities", [])
        child_entities: list[EntityLine] = []
        for child_raw in child_ids_raw:
            try:
                child_id = UUID(str(child_raw))
            except ValueError:
                continue
            child = entity_service.get(child_id)
            if child is None:
                continue
            child_entities.append(
                EntityLine(
                    entity_id=str(child.id),
                    entity_type=child.entity_type,
                    title=child.title,
                    description=child.description,
                )
            )

        focus_uuid: UUID | None = None
        if focus_entity_raw:
            try:
                focus_uuid = UUID(focus_entity_raw)
            except ValueError:
                focus_uuid = None
        if focus_uuid is None:
            focus_uuid = workspace_uuid

        focus_entity = entity_service.get(focus_uuid)
        focus_line: EntityLine | None = None
        if focus_entity is not None and focus_uuid != workspace_uuid:
            focus_line = EntityLine(
                entity_id=str(focus_entity.id),
                entity_type=focus_entity.entity_type,
                title=focus_entity.title,
                description=focus_entity.description,
            )

        graph_lines = relationship_service.traverse_context_snippets(
            focus_uuid,
            entity_service,
            max_depth=max_depth,
        )

        compiled = compile_workspace_snapshot(
            workspace_id=str(workspace.id),
            workspace_title=workspace.title,
            child_entities=child_entities or None,
            focus_entity=focus_line,
            relationship_lines=graph_lines or None,
        )
        snippets = [compiled] if compiled else []

        _publish_result(
            bus,
            WORKSPACE_CONTEXT_RESULT,
            rid,
            {
                "snippets": snippets,
                "workspace_id": workspace_id_raw,
                "entity_id": str(focus_uuid),
            },
            source=source,
        )

    def on_relationship_create_request(event: Event) -> None:
        rid = _request_id(event)
        payload = event.payload
        try:
            rel_type = RelationshipType(str(payload["relationship_type"]))
            relationship = relationship_service.create(
                source_id=UUID(str(payload["source_id"])),
                target_id=UUID(str(payload["target_id"])),
                relationship_type=rel_type,
                metadata=dict(payload.get("metadata") or {}),
            )
            _publish_result(
                bus,
                RELATIONSHIP_CREATE_RESULT,
                rid,
                {
                    "relationship_id": str(relationship.id),
                    "source_id": str(relationship.source_id),
                    "target_id": str(relationship.target_id),
                    "relationship_type": relationship.relationship_type.value,
                },
                source=source,
            )
            _record_reversible_timeline(
                timeline_service,
                event_type="relationship.created",
                entity_id=relationship.source_id,
                entity_type=None,
                payload={
                    "relationship_id": str(relationship.id),
                    "target_id": str(relationship.target_id),
                    "relationship_type": relationship.relationship_type.value,
                },
                undo_data={
                    "action": UNDO_DELETE_RELATIONSHIP,
                    "relationship_id": str(relationship.id),
                },
            )
        except Exception as exc:  # noqa: BLE001
            _publish_result(
                bus,
                RELATIONSHIP_CREATE_RESULT,
                rid,
                {"error": str(exc)},
                source=source,
            )

    def on_workspace_create_request(event: Event) -> None:
        rid = _request_id(event)
        payload = event.payload
        try:
            workspace = workspace_service.create(
                title=str(payload["title"]),
                description=str(payload.get("description", "")),
            )
            workspace_service.activate(workspace.id)
            _publish_result(
                bus,
                WORKSPACE_CREATE_RESULT,
                rid,
                {
                    "workspace_id": str(workspace.id),
                    "title": workspace.title,
                },
                source=source,
            )
            _record_reversible_timeline(
                timeline_service,
                event_type="workspace.created",
                entity_id=workspace.id,
                entity_type=ENTITY_TYPE_WORKSPACE,
                payload={"title": workspace.title},
                undo_data={
                    "action": UNDO_DELETE_ENTITY,
                    "entity_id": str(workspace.id),
                },
            )
        except Exception as exc:  # noqa: BLE001
            _publish_result(
                bus,
                WORKSPACE_CREATE_RESULT,
                rid,
                {"error": str(exc)},
                source=source,
            )

    def on_workspace_add_entity_request(event: Event) -> None:
        rid = _request_id(event)
        payload = event.payload
        try:
            workspace = workspace_service.add_entity(
                workspace_id=UUID(str(payload["workspace_id"])),
                entity_id=UUID(str(payload["entity_id"])),
            )
            _publish_result(
                bus,
                WORKSPACE_ADD_ENTITY_RESULT,
                rid,
                {
                    "workspace_id": str(workspace.id),
                    "entity_id": str(payload["entity_id"]),
                },
                source=source,
            )
            entity_id = UUID(str(payload["entity_id"]))
            _record_reversible_timeline(
                timeline_service,
                event_type="workspace.entity.added",
                entity_id=entity_id,
                entity_type=None,
                payload={
                    "workspace_id": str(workspace.id),
                    "entity_id": str(entity_id),
                },
                undo_data={
                    "action": UNDO_REMOVE_WORKSPACE_ENTITY,
                    "workspace_id": str(workspace.id),
                    "entity_id": str(entity_id),
                },
            )
        except Exception as exc:  # noqa: BLE001
            _publish_result(
                bus,
                WORKSPACE_ADD_ENTITY_RESULT,
                rid,
                {"error": str(exc)},
                source=source,
            )

    def on_ui_select_entity(event: Event) -> None:
        entity_id_raw = str(event.payload.get("entity_id", "")).strip()
        entity_type = str(event.payload.get("entity_type", "")).strip()
        workspace_id_raw = str(event.payload.get("workspace_id", "")).strip()
        target_ws: UUID | None = None
        if workspace_id_raw:
            try:
                target_ws = UUID(workspace_id_raw)
            except ValueError:
                target_ws = None
        elif entity_type == ENTITY_TYPE_WORKSPACE and entity_id_raw:
            try:
                target_ws = UUID(entity_id_raw)
            except ValueError:
                target_ws = None
        elif entity_id_raw:
            try:
                target_ws = _resolve_parent_workspace_id(
                    entity_service,
                    relationship_service,
                    UUID(entity_id_raw),
                    entity_type,
                )
            except ValueError:
                target_ws = None
        if target_ws is not None:
            try:
                workspace_service.activate(target_ws)
            except ValueError:
                pass

    def on_ui_select_workspace(event: Event) -> None:
        workspace_id_raw = str(event.payload.get("workspace_id", "")).strip()
        if not workspace_id_raw:
            workspace_service.deactivate()
            return
        try:
            workspace_service.activate(UUID(workspace_id_raw))
        except ValueError:
            pass

    def on_service_ready(event: Event) -> None:
        if str(event.payload.get("service", "")).strip() != "workspace_os":
            return
        if workspace_service.get_active() is not None:
            return
        workspaces = workspace_service.get_all()
        if workspaces:
            workspace_service.activate(workspaces[0].id)

    def on_timeline_record_request(event: Event) -> None:
        rid = _request_id(event)
        payload = event.payload
        try:
            entity_id_raw = payload.get("entity_id")
            entity_id = UUID(str(entity_id_raw)) if entity_id_raw else None
            timeline_service.record(
                event_type=str(payload["event_type"]),
                entity_id=entity_id,
                entity_type=str(payload.get("entity_type", "")) or None,
                payload=dict(payload.get("payload") or {}),
                reversible=bool(payload.get("reversible", False)),
                undo_data=dict(payload["undo_data"]) if payload.get("undo_data") else None,
            )
            _publish_result(
                bus,
                TIMELINE_RECORD_RESULT,
                rid,
                {"recorded": True},
                source=source,
            )
        except Exception as exc:  # noqa: BLE001
            _publish_result(
                bus,
                TIMELINE_RECORD_RESULT,
                rid,
                {"error": str(exc)},
                source=source,
            )

    def on_action_invoke_request(event: Event) -> None:
        rid = _request_id(event)
        payload = event.payload
        action_type = str(payload.get("action_type", "launch"))
        action_name = str(payload.get("action_name", ""))
        parameters = dict(payload.get("parameters") or {})
        actions = [
            a for a in action_registry.get_by_type(action_type) if a.name == action_name
        ]
        if not actions:
            _publish_result(
                bus,
                ACTION_INVOKE_RESULT,
                rid,
                {"error": f"Launch action not found: {action_name}"},
                source=source,
            )
            return
        try:
            action_registry.invoke(actions[0].id, parameters=parameters)
            _publish_result(
                bus,
                ACTION_INVOKE_RESULT,
                rid,
                {"action_id": str(actions[0].id), "action_name": action_name},
                source=source,
            )
        except Exception as exc:  # noqa: BLE001
            _publish_result(
                bus,
                ACTION_INVOKE_RESULT,
                rid,
                {"error": str(exc)},
                source=source,
            )

    subs = [
        bus.subscribe(ENTITY_CREATE_REQUEST, on_entity_create_request),
        bus.subscribe(ENTITY_SEARCH_REQUEST, on_entity_search_request),
        bus.subscribe(ENTITY_CONTEXT_REQUEST, on_entity_context_request),
        bus.subscribe(WORKSPACE_CONTEXT_REQUEST, on_workspace_context_request),
        bus.subscribe(RELATIONSHIP_CREATE_REQUEST, on_relationship_create_request),
        bus.subscribe(WORKSPACE_CREATE_REQUEST, on_workspace_create_request),
        bus.subscribe(WORKSPACE_ADD_ENTITY_REQUEST, on_workspace_add_entity_request),
        bus.subscribe(UI_SELECT_ENTITY, on_ui_select_entity),
        bus.subscribe(UI_SELECT_WORKSPACE, on_ui_select_workspace),
        bus.subscribe(SERVICE_READY, on_service_ready),
        bus.subscribe(TIMELINE_RECORD_REQUEST, on_timeline_record_request),
        bus.subscribe(ACTION_INVOKE_REQUEST, on_action_invoke_request),
    ]
    return subs


# Re-export resource type keys for orchestrators (avoid duplicating mapping).
RESOURCE_VALUE_KEYS = {
    RESOURCE_TYPE_URL: "url",
    RESOURCE_TYPE_FOLDER: "path",
    RESOURCE_TYPE_COMMAND: "command",
}
