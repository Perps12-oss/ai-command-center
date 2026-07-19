"""State-domain capability tools — notes, memory, navigate."""

from __future__ import annotations

from typing import Any, Protocol

from ai_command_center.core.events.topics import UI_NAVIGATE
from ai_command_center.core.tools import ToolResult, ToolSpec


class _NoteOps(Protocol):
    def create_note(self, body: str) -> tuple[bool, str, str]: ...
    def search_notes(self, query: str) -> tuple[bool, str, list[dict[str, str]]]: ...


class _MemoryOps(Protocol):
    def store_memory(
        self,
        body: str,
        *,
        workspace_id: str = "",
        entity_id: str = "",
    ) -> tuple[bool, str, dict[str, Any]]: ...

    def query_memory(
        self,
        query: str,
        *,
        workspace_id: str = "",
        entity_id: str = "",
    ) -> tuple[bool, str, list[dict[str, Any]]]: ...


def bind_state_capability_tools(
    registry: Any,
    *,
    bus: Any,
    notes: _NoteOps | None = None,
    memory: _MemoryOps | None = None,
) -> None:
    """Register notes/memory/navigate tools on the shared ToolRegistry."""

    def _register(spec: ToolSpec) -> None:
        existing = None
        if hasattr(registry, "get_spec"):
            existing = registry.get_spec(spec.name)
        elif hasattr(registry, "get"):
            existing = registry.get(spec.name)
        if existing is not None:
            return
        if hasattr(registry, "register_tool"):
            registry.register_tool(spec)
        elif hasattr(registry, "register"):
            registry.register(spec)

    def notes_create(args: dict[str, Any]) -> ToolResult:
        if notes is None:
            return ToolResult(success=False, error="notes provider unavailable")
        body = str(args.get("body") or args.get("text") or "").strip()
        ok, message, path = notes.create_note(body)
        return ToolResult(success=ok, output=message if ok else "", error=None if ok else message)

    def notes_search(args: dict[str, Any]) -> ToolResult:
        if notes is None:
            return ToolResult(success=False, error="notes provider unavailable")
        query = str(args.get("query") or args.get("text") or "").strip()
        ok, message, hits = notes.search_notes(query)
        if not ok:
            return ToolResult(success=False, error=message)
        lines = [f"{h.get('title', '')}: {h.get('snippet', '')}" for h in hits[:10]]
        output = message if not lines else "\n".join(lines)
        return ToolResult(success=True, output=output or "no matches")

    def memory_store(args: dict[str, Any]) -> ToolResult:
        if memory is None:
            return ToolResult(success=False, error="memory provider unavailable")
        body = str(args.get("body") or args.get("text") or "").strip()
        ok, message, meta = memory.store_memory(
            body,
            workspace_id=str(args.get("workspace_id") or ""),
            entity_id=str(args.get("entity_id") or ""),
        )
        return ToolResult(
            success=ok,
            output=message if ok else "",
            error=None if ok else message,
        )

    def memory_query(args: dict[str, Any]) -> ToolResult:
        if memory is None:
            return ToolResult(success=False, error="memory provider unavailable")
        query = str(args.get("query") or args.get("text") or "").strip()
        ok, message, hits = memory.query_memory(
            query,
            workspace_id=str(args.get("workspace_id") or ""),
            entity_id=str(args.get("entity_id") or ""),
        )
        if not ok:
            return ToolResult(success=False, error=message)
        if not hits:
            return ToolResult(success=True, output="no memories matched")
        lines = [f"{h.get('label', '')}: {h.get('content', '')}" for h in hits[:10]]
        return ToolResult(success=True, output="\n".join(lines))

    def navigate(args: dict[str, Any]) -> ToolResult:
        view = str(args.get("view") or "home").strip().lower() or "home"
        bus.publish(UI_NAVIGATE, {"view": view}, source="state_capability_tools")
        return ToolResult(success=True, output=f"navigated:{view}")

    for spec in (
        ToolSpec(name="notes.create", description="Create a vault note", handler=notes_create),
        ToolSpec(name="notes.search", description="Search vault notes", handler=notes_search),
        ToolSpec(name="memory.store", description="Store a memory item", handler=memory_store),
        ToolSpec(name="memory.query", description="Query stored memories", handler=memory_query),
        ToolSpec(name="navigate", description="Navigate to a UI view", handler=navigate),
    ):
        _register(spec)
