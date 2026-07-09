"""Dense structural compiler for workspace entity graph → LLM prompt text.

Pure formatting only — no bus, database, or service access.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EntityLine:
    """Minimal entity row for snapshot compilation."""

    entity_id: str
    entity_type: str
    title: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class RelationshipLine:
    """Directed edge for snapshot compilation."""

    predicate: str
    target_type: str
    target_title: str
    target_id: str
    direction: str = "outgoing"  # outgoing | incoming


def _truncate_lines(lines: list[str], max_lines: int) -> list[str]:
    if len(lines) <= max_lines:
        return lines
    omitted = len(lines) - max_lines + 1
    return lines[: max_lines - 1] + [f"  … (+{omitted} more lines truncated)"]


def _format_entity_detail(entity: EntityLine, *, indent: str = "  ") -> list[str]:
    lines = [f"{indent}{entity.entity_type}: \"{entity.title}\" (id={entity.entity_id})"]
    if entity.description.strip():
        lines.append(f"{indent}  desc: {entity.description.strip()}")
    return lines


def compile_workspace_snapshot(
    *,
    workspace_id: str,
    workspace_title: str,
    child_entities: list[EntityLine] | None = None,
    focus_entity: EntityLine | None = None,
    relationship_lines: list[str] | None = None,
    max_lines: int = 80,
) -> str:
    """Compile active workspace + children + focus + graph into one dense block."""
    workspace_id = workspace_id.strip()
    workspace_title = workspace_title.strip()
    if not workspace_id:
        return ""

    lines: list[str] = [
        f"[WORKSPACE] {workspace_title} (id={workspace_id})",
    ]

    children = child_entities or []
    if children:
        lines.append("  ENTITIES:")
        child_rows: list[str] = []
        for child in children:
            child_rows.extend(_format_entity_detail(child, indent="    "))
        lines.extend(_truncate_lines(child_rows, max(4, max_lines // 2)))

    if focus_entity is not None and focus_entity.entity_id != workspace_id:
        lines.append("  FOCUS:")
        lines.extend(_format_entity_detail(focus_entity, indent="    "))

    if relationship_lines:
        lines.append("  GRAPH:")
        graph_rows = [f"    {line.lstrip()}" for line in relationship_lines if line.strip()]
        lines.extend(_truncate_lines(graph_rows, max(4, max_lines // 3)))

    if len(lines) > max_lines:
        lines = _truncate_lines(lines, max_lines)

    return "\n".join(lines)


def compile_entity_focus(
    *,
    entity_id: str,
    entity_type: str,
    entity_title: str,
    entity_description: str = "",
    resource_fields: dict[str, str] | None = None,
    outgoing_edges: list[RelationshipLine] | None = None,
    incoming_edges: list[RelationshipLine] | None = None,
    max_lines: int = 60,
) -> str:
    """Compile a single entity focus block with relationship edges."""
    entity_id = entity_id.strip()
    if not entity_id:
        return ""

    entity = EntityLine(
        entity_id=entity_id,
        entity_type=entity_type.strip() or "entity",
        title=entity_title.strip() or entity_id,
        description=entity_description.strip(),
    )

    lines: list[str] = [f"[ENTITY] {entity.entity_type}: \"{entity.title}\" (id={entity.entity_id})"]
    if entity.description:
        lines.append(f"  desc: {entity.description}")

    fields = resource_fields or {}
    for key in ("resource_type", "url", "path", "command", "plugin_id"):
        value = str(fields.get(key, "")).strip()
        if value:
            lines.append(f"  {key}: {value}")

    out_edges = outgoing_edges or []
    in_edges = incoming_edges or []
    if out_edges or in_edges:
        lines.append("  EDGES:")
        edge_rows: list[str] = []
        for edge in out_edges:
            predicate = edge.predicate.upper().replace(" ", "_")
            edge_rows.append(
                f"    {predicate} -> {edge.target_type}: "
                f"\"{edge.target_title}\" (id={edge.target_id})"
            )
        for edge in in_edges:
            predicate = edge.predicate.upper().replace(" ", "_")
            edge_rows.append(
                f"    <-{predicate}- {edge.target_type}: "
                f"\"{edge.target_title}\" (id={edge.target_id})"
            )
        lines.extend(_truncate_lines(edge_rows, max(4, max_lines // 2)))

    if len(lines) > max_lines:
        lines = _truncate_lines(lines, max_lines)

    return "\n".join(lines)
