"""Opt-in memory graph — no background ingestion (Phase 4E)."""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    MEMORY_CLEAR_SELECTION,
    MEMORY_CLEARED,
    MEMORY_DELETE_REQUEST,
    MEMORY_ERROR,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    MEMORY_REMEMBER,
    MEMORY_SELECT,
    MEMORY_STORED,
    MEMORY_SELECTED,
    WORKSPACE_ACTIVE,
    WORKSPACE_DEACTIVATED,
)
from ai_command_center.repositories.memory_repository import MemoryRepository
from ai_command_center.services.base import BaseService


class MemoryGraphService(BaseService):
    name = "memory_graph"

    def __init__(self, bus, repo: MemoryRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._selected_snippets: list[str] = []
        self._active_workspace_id: str = ""
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(MEMORY_REMEMBER, self._on_remember)
        )
        self._unsubscribers.append(
            self._bus.subscribe(MEMORY_SELECT, self._on_select)
        )
        self._unsubscribers.append(
            self._bus.subscribe(MEMORY_CLEAR_SELECTION, self._on_clear)
        )
        # Memory executes via memory.store / memory.query tools.
        self._unsubscribers.append(
            self._bus.subscribe(MEMORY_LOOKUP_REQUEST, self._on_lookup_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(MEMORY_DELETE_REQUEST, self._on_delete_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_ACTIVE, self._on_workspace_active)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_DEACTIVATED, self._on_workspace_deactivated)
        )

    def _on_workspace_active(self, event: Event) -> None:
        self._active_workspace_id = str(event.payload.get("workspace_id", "")).strip()

    def _on_workspace_deactivated(self, event: Event) -> None:
        cleared = str(event.payload.get("workspace_id", "")).strip()
        if not cleared or cleared == self._active_workspace_id:
            self._active_workspace_id = ""

    def _default_workspace_id(self, explicit: str = "") -> str:
        return explicit.strip() or self._active_workspace_id

    def _resolve_entity_id(self, payload: dict) -> str:
        return str(
            payload.get("workspace_entity_id") or payload.get("entity_id", "")
        ).strip()

    def _resolve_memory_scope(
        self, payload: dict
    ) -> tuple[str, str, bool]:
        """Resolve workspace/entity scope; global search requires explicit opt-in."""
        global_search = bool(payload.get("global_search", False))
        if global_search:
            return "", "", True
        workspace_id = self._default_workspace_id(str(payload.get("workspace_id", "")))
        entity_id = self._resolve_entity_id(payload)
        return workspace_id, entity_id, False

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def get_context_snippets(self) -> list[str]:
        return list(self._selected_snippets)

    def _on_delete_request(self, event: Event) -> None:
        node_id = str(event.payload.get("id", ""))
        if not node_id:
            self._bus.publish(
                MEMORY_ERROR,
                {"message": "Delete request missing memory id"},
                source=self.name,
            )
            return
        deleted = self._repo.delete(node_id)
        if deleted:
            self._bus.publish(
                MEMORY_CLEARED,
                {"id": node_id},
                source=self.name,
            )
        else:
            self._bus.publish(
                MEMORY_ERROR,
                {"message": f"Memory not found: {node_id}"},
                source=self.name,
            )

    def store_memory(
        self,
        body: str,
        *,
        workspace_id: str = "",
        entity_id: str = "",
    ) -> tuple[bool, str, dict]:
        """Capability API used by memory.store tool."""
        if not body:
            return False, "remember: requires label | content", {}
        if "|" in body:
            label, content = (part.strip() for part in body.split("|", 1))
        else:
            label, _, content = body.partition(" ")
            label, content = label.strip(), content.strip()
        if not label or not content:
            return False, "remember: use 'label | content' or 'label content...'", {}
        ws = workspace_id or self._active_workspace_id
        node_id = self._repo.remember(
            label=label,
            content=content,
            kind="entity",
            tier="mid",
            related_to=None,
            relation="relates_to",
            workspace_id=ws,
            entity_id=entity_id,
        )
        meta = {
            "id": node_id,
            "label": label,
            "content": content,
            "workspace_id": ws,
            "entity_id": entity_id,
        }
        self._bus.publish(MEMORY_STORED, meta, source=self.name)
        return True, f"stored memory {label}", meta

    def query_memory(
        self,
        query: str,
        *,
        workspace_id: str = "",
        entity_id: str = "",
    ) -> tuple[bool, str, list[dict]]:
        """Capability API used by memory.query tool."""
        if not query:
            return False, "memory: requires a search query", []
        ws = workspace_id or self._active_workspace_id
        nodes = self._search_nodes(
            query,
            workspace_id=ws,
            entity_id=entity_id,
            global_search=not bool(ws),
        )
        hits = [
            {"id": n.id, "label": n.label, "content": n.content}
            for n in nodes[:10]
        ]
        snippets = [f"[memory:{h['label']}]\n{h['content']}" for h in hits[:3]]
        self._selected_snippets = snippets
        self._bus.publish(
            MEMORY_SELECTED,
            {"query": query, "results": hits, "snippets": snippets},
            source=self.name,
        )
        return True, f"found {len(hits)} memories", hits

    def lookup_for_state(self, query: str, *, workspace_id: str = "") -> list[dict]:
        """StateAuthority memory projection helper (read-only; no bus side-effects)."""
        if not query.strip():
            return []
        ws = workspace_id or self._active_workspace_id
        nodes = self._search_nodes(
            query,
            workspace_id=ws,
            entity_id="",
            global_search=not bool(ws),
        )
        return [
            {"id": n.id, "label": n.label, "content": n.content}
            for n in nodes[:10]
        ]

    def _search_nodes(
        self,
        query: str,
        *,
        workspace_id: str,
        entity_id: str,
        global_search: bool,
    ):
        return self._repo.search(
            query,
            workspace_id=workspace_id,
            entity_id=entity_id,
            global_search=global_search,
        )

    def _on_lookup_request(self, event: Event) -> None:
        query = str(event.payload.get("query", "")).strip()
        workspace_id, entity_id, global_search = self._resolve_memory_scope(
            dict(event.payload)
        )
        snippets: list[str] = []
        if query:
            nodes = self._search_nodes(
                query,
                workspace_id=workspace_id,
                entity_id=entity_id,
                global_search=global_search,
            )
            snippets = [f"[memory:{n.label}]\n{n.content}" for n in nodes[:3]]
        self._bus.publish(
            MEMORY_LOOKUP_RESULT,
            {
                "request_id": event.payload.get("request_id", ""),
                "snippets": snippets,
                "source": self.name,
            },
            source=self.name,
        )

    def _on_remember(self, event: Event) -> None:
        label = str(event.payload.get("label", "")).strip()
        content = str(event.payload.get("content", "")).strip()
        if not label or not content:
            self._bus.publish(
                MEMORY_ERROR,
                {"message": "memory.remember requires label and content"},
                source=self.name,
            )
            return
        workspace_id, entity_id, global_search = self._resolve_memory_scope(
            dict(event.payload)
        )
        if global_search:
            workspace_id = ""
            entity_id = ""
        node_id = self._repo.remember(
            label=label,
            content=content,
            kind=str(event.payload.get("kind", "entity")),
            tier=str(event.payload.get("tier", "mid")),
            related_to=event.payload.get("related_to"),
            relation=str(event.payload.get("relation", "relates_to")),
            workspace_id=workspace_id,
            entity_id=entity_id,
        )
        self._bus.publish(
            MEMORY_STORED,
            {
                "id": node_id,
                "label": label,
                "workspace_id": workspace_id,
                "entity_id": entity_id,
            },
            source=self.name,
        )

    def _on_select(self, event: Event) -> None:
        query = str(event.payload.get("query", "")).strip()
        node_id = str(event.payload.get("id", "")).strip()
        workspace_id, entity_id, global_search = self._resolve_memory_scope(
            dict(event.payload)
        )
        nodes = []
        if node_id:
            node = self._repo.get(node_id)
            if node:
                nodes = [node]
        elif query:
            nodes = self._search_nodes(
                query,
                workspace_id=workspace_id,
                entity_id=entity_id,
                global_search=global_search,
            )
        if not nodes:
            self._bus.publish(
                MEMORY_ERROR,
                {"message": "no memory nodes matched selection"},
                source=self.name,
            )
            return
        self._selected_snippets = [f"[memory:{n.label}]\n{n.content}" for n in nodes[:3]]
        self._bus.publish(
            MEMORY_SELECTED,
            {"count": len(self._selected_snippets), "labels": [n.label for n in nodes[:3]]},
            source=self.name,
        )

    def _on_clear(self, _event: Event) -> None:
        self._selected_snippets.clear()
        self._bus.publish(MEMORY_CLEARED, {}, source=self.name)
