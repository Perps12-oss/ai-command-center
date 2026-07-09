"""Tests for world model context compiler."""

from __future__ import annotations

from ai_command_center.core.world_model.context_compiler import (
    EntityLine,
    RelationshipLine,
    compile_entity_focus,
    compile_workspace_snapshot,
)


def test_compile_workspace_snapshot_includes_workspace_children_and_graph() -> None:
    compiled = compile_workspace_snapshot(
        workspace_id="ws-1",
        workspace_title="Home",
        child_entities=[
            EntityLine("t-1", "task", "Shopping List"),
            EntityLine("n-1", "note", "Bread"),
        ],
        focus_entity=EntityLine("t-1", "task", "Shopping List"),
        relationship_lines=[
            '  depth-1: note "Bread" (n-1)',
            '  depth-1: note "Eggs" (n-2)',
        ],
    )

    assert "[WORKSPACE] Home (id=ws-1)" in compiled
    assert "ENTITIES:" in compiled
    assert 'task: "Shopping List"' in compiled
    assert "FOCUS:" in compiled
    assert "GRAPH:" in compiled
    assert "Bread" in compiled


def test_compile_workspace_snapshot_truncates_at_max_lines() -> None:
    children = [
        EntityLine(f"id-{i}", "note", f"Item {i}") for i in range(20)
    ]
    compiled = compile_workspace_snapshot(
        workspace_id="ws-1",
        workspace_title="Home",
        child_entities=children,
        max_lines=8,
    )

    assert "truncated" in compiled
    assert compiled.count("\n") < 20


def test_compile_entity_focus_renders_outgoing_and_incoming_edges() -> None:
    compiled = compile_entity_focus(
        entity_id="t-1",
        entity_type="task",
        entity_title="Shopping List",
        entity_description="Groceries",
        outgoing_edges=[
            RelationshipLine("contains", "note", "Bread", "n-1"),
        ],
        incoming_edges=[
            RelationshipLine(
                "part_of",
                "workspace",
                "Home",
                "ws-1",
                direction="incoming",
            ),
        ],
    )

    assert "[ENTITY] task: \"Shopping List\" (id=t-1)" in compiled
    assert "desc: Groceries" in compiled
    assert "CONTAINS -> note:" in compiled
    assert "<-PART_OF-" in compiled


def test_compile_entity_focus_includes_resource_fields() -> None:
    compiled = compile_entity_focus(
        entity_id="r-1",
        entity_type="resource",
        entity_title="Project folder",
        resource_fields={
            "resource_type": "folder",
            "path": "C:/Projects/demo",
        },
    )

    assert "resource_type: folder" in compiled
    assert "path: C:/Projects/demo" in compiled


def test_compile_workspace_snapshot_empty_without_workspace_id() -> None:
    assert compile_workspace_snapshot(workspace_id="", workspace_title="Home") == ""
