"""Entity context snippet formatting for bus-driven prompt injection (W3)."""

from __future__ import annotations


def format_entity_context(entity: dict[str, object]) -> str | None:
    """Format a workspace entity (+ optional resource fields) for prompt injection."""
    entity_id = str(entity.get("entity_id", "")).strip()
    if not entity_id:
        return None
    entity_type = str(entity.get("entity_type", "entity"))
    entity_title = str(entity.get("entity_title", entity_id))
    lines = [f"Workspace {entity_type}: {entity_title} (entity_id={entity_id})"]
    description = str(entity.get("entity_description", "")).strip()
    resource_type = str(entity.get("resource_type", "")).strip()
    plugin_id = str(entity.get("plugin_id", "")).strip()
    url = str(entity.get("url", "")).strip()
    path = str(entity.get("path", "")).strip()
    command = str(entity.get("command", "")).strip()
    if description:
        lines.append(f"Description: {description}")
    if resource_type:
        lines.append(f"Resource type: {resource_type}")
    if plugin_id:
        lines.append(f"Plugin id: {plugin_id}")
    if url:
        lines.append(f"URL: {url}")
    if path:
        lines.append(f"Path: {path}")
    if command:
        lines.append(f"Command: {command}")
    return "\n".join(lines)
