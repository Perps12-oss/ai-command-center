"""Timeline undo handler tests (P1 backlog)."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from ai_command_center.core.entity.entity import ENTITY_TYPE_CARD
from ai_command_center.core.entity.entity_bus_handlers import register_entity_bus_handlers
from ai_command_center.core.entity.entity_repository import EntityRepository
from ai_command_center.core.entity.entity_service import EntityService
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    ENTITY_CREATE_REQUEST,
    ENTITY_CREATE_RESULT,
    RELATIONSHIP_CREATE_REQUEST,
    RELATIONSHIP_CREATE_RESULT,
    TIMELINE_UNDO_RESULT,
    WORKSPACE_ADD_ENTITY_REQUEST,
    WORKSPACE_ADD_ENTITY_RESULT,
    WORKSPACE_CREATE_REQUEST,
    WORKSPACE_CREATE_RESULT,
)
from ai_command_center.core.relationship.relationship import RelationshipType
from ai_command_center.core.relationship.relationship_repository import RelationshipRepository
from ai_command_center.core.relationship.relationship_service import RelationshipService
from ai_command_center.core.timeline.timeline_repository import TimelineRepository
from ai_command_center.core.timeline.timeline_service import TimelineService
from ai_command_center.core.timeline.timeline_undo_handlers import register_timeline_undo_handlers
from ai_command_center.core.workspace.workspace_service import WorkspaceService
from ai_command_center.db.connection import connect, init_database


def _capture_result(bus: EventBus, topic: str) -> dict:
    captured: dict = {}

    def on_result(event) -> None:
        rid = str(event.payload.get("request_id", ""))
        if rid:
            captured[rid] = dict(event.payload)

    unsub = bus.subscribe(topic, on_result)
    return captured, unsub


def _workspace_stack() -> tuple[EventBus, EntityService, RelationshipService, WorkspaceService, TimelineService]:
    bus = EventBus()
    db = init_database(connect(Path(":memory:")))
    entity_service = EntityService(EntityRepository(db), bus)
    relationship_service = RelationshipService(RelationshipRepository(db), bus)
    workspace_service = WorkspaceService(entity_service, bus)
    timeline_service = TimelineService(TimelineRepository(db), bus)
    register_entity_bus_handlers(
        bus,
        entity_service=entity_service,
        relationship_service=relationship_service,
        workspace_service=workspace_service,
        timeline_service=timeline_service,
        action_registry=__import__(
            "ai_command_center.core.action.action_registry", fromlist=["ActionRegistry"]
        ).ActionRegistry(bus),
    )
    register_timeline_undo_handlers(
        bus,
        entity_service=entity_service,
        relationship_service=relationship_service,
        workspace_service=workspace_service,
    )
    return bus, entity_service, relationship_service, workspace_service, timeline_service


def test_entity_create_records_reversible_timeline_and_undo_deletes() -> None:
    bus, entity_service, _, _, timeline_service = _workspace_stack()
    results, unsub_result = _capture_result(bus, ENTITY_CREATE_RESULT)
    rid = "req-entity-1"
    bus.publish(
        ENTITY_CREATE_REQUEST,
        {
            "request_id": rid,
            "entity_type": ENTITY_TYPE_CARD,
            "title": "Undo Me",
        },
        source="test",
    )
    unsub_result()
    result = results.get(rid) or {}
    assert "error" not in result
    entity_id = UUID(str(result["entity_id"]))
    assert entity_service.get(entity_id) is not None

    reversible = timeline_service.get_reversible(limit=5)
    assert len(reversible) == 1
    assert reversible[0].reversible is True
    assert reversible[0].undo_data is not None
    assert reversible[0].undo_data.get("action") == "delete_entity"

    undo_results: list[dict] = []
    unsub = bus.subscribe(
        TIMELINE_UNDO_RESULT,
        lambda event: undo_results.append(dict(event.payload)),
    )
    try:
        assert timeline_service.undo(reversible[0].id) is True
    finally:
        unsub()

    assert entity_service.get(entity_id) is None
    assert undo_results
    assert undo_results[0]["success"] is True
    assert undo_results[0]["action"] == "delete_entity"


def test_relationship_create_undo_deletes_relationship() -> None:
    bus, entity_service, relationship_service, _, timeline_service = _workspace_stack()
    source = entity_service.create(entity_type=ENTITY_TYPE_CARD, title="Source")
    target = entity_service.create(entity_type=ENTITY_TYPE_CARD, title="Target")

    rid = "req-rel-1"
    results, unsub_result = _capture_result(bus, RELATIONSHIP_CREATE_RESULT)
    bus.publish(
        RELATIONSHIP_CREATE_REQUEST,
        {
            "request_id": rid,
            "source_id": str(source.id),
            "target_id": str(target.id),
            "relationship_type": RelationshipType.CONTAINS.value,
        },
        source="test",
    )
    unsub_result()
    result = results.get(rid) or {}
    relationship_id = UUID(str(result["relationship_id"]))
    assert relationship_service.get(relationship_id) is not None

    reversible = timeline_service.get_reversible(limit=1)
    assert reversible
    assert timeline_service.undo(reversible[0].id) is True
    assert relationship_service.get(relationship_id) is None


def test_workspace_add_entity_undo_removes_from_workspace() -> None:
    bus, entity_service, _, workspace_service, timeline_service = _workspace_stack()
    ws_rid = "req-ws-1"
    ws_results, unsub_ws = _capture_result(bus, WORKSPACE_CREATE_RESULT)
    bus.publish(
        WORKSPACE_CREATE_REQUEST,
        {"request_id": ws_rid, "title": "WS"},
        source="test",
    )
    unsub_ws()
    ws_result = ws_results.get(ws_rid) or {}
    workspace_id = UUID(str(ws_result["workspace_id"]))
    card = entity_service.create(entity_type=ENTITY_TYPE_CARD, title="Canvas Card")

    add_rid = "req-add-1"
    add_results, unsub_add = _capture_result(bus, WORKSPACE_ADD_ENTITY_RESULT)
    bus.publish(
        WORKSPACE_ADD_ENTITY_REQUEST,
        {
            "request_id": add_rid,
            "workspace_id": str(workspace_id),
            "entity_id": str(card.id),
        },
        source="test",
    )
    unsub_add()
    workspace = workspace_service.get(workspace_id)
    assert workspace is not None
    assert str(card.id) in workspace.metadata.get("entities", [])

    reversible = [event for event in timeline_service.get_reversible() if event.event_type == "workspace.entity.added"]
    assert reversible
    assert timeline_service.undo(reversible[-1].id) is True

    workspace = workspace_service.get(workspace_id)
    assert workspace is not None
    assert str(card.id) not in workspace.metadata.get("entities", [])
    assert entity_service.get(card.id) is not None


def test_unsupported_undo_action_publishes_failure() -> None:
    bus, entity_service, relationship_service, workspace_service, timeline_service = _workspace_stack()
    recorded = timeline_service.record(
        event_type="custom.event",
        reversible=True,
        undo_data={"action": "unsupported_action"},
    )
    results: list[dict] = []
    unsub = bus.subscribe(
        TIMELINE_UNDO_RESULT,
        lambda event: results.append(dict(event.payload)),
    )
    try:
        timeline_service.undo(recorded.id)
    finally:
        unsub()
    assert results
    assert results[0]["success"] is False
    assert "unsupported" in str(results[0]["detail"])
