"""Opt-in memory graph — no background ingestion (Phase 4E)."""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    COMMAND_ROUTED,
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
from ai_command_center.core.events.intents import INTENT_MEMORY_REMEMBER, INTENT_MEMORY_SELECT


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
        self._unsubscribers.append(
            self._bus.subscribe(COMMAND_ROUTED, self._on_command_routed)
        )
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

    def _on_command_routed(self, event: Event) -> None:
        from ai_command_center.core.routing_authority import is_routing_authority

        if not is_routing_authority(event.source):
            return
        intent = event.payload.get("intent")
        args = event.payload.get("args") or {}
        merged = {**args, **event.payload}
        workspace_id, entity_id, global_search = self._resolve_memory_scope(merged)
        if intent == INTENT_MEMORY_REMEMBER:
            self._handle_remember_command(
                str(args.get("body", "")),
                workspace_id=workspace_id,
                entity_id=entity_id,
                global_search=global_search,
            )
        elif intent == INTENT_MEMORY_SELECT:
            self._handle_select_command(
                str(args.get("query", "")),
                workspace_id=workspace_id,
                entity_id=entity_id,
                global_search=global_search,
            )

    def _handle_remember_command(
        self,
        body: str,
        *,
        workspace_id: str = "",
        entity_id: str = "",
        global_search: bool = False,
    ) -> None:
        if not body:
            self._bus.publish(
                MEMORY_ERROR,
                {"message": "remember: requires label | content (example: remember: api-key | sk-...)"},
                source=self.name,
            )
            return
        if "|" in body:
            label, content = (part.strip() for part in body.split("|", 1))
        else:
            label, _, content = body.partition(" ")
        if not label or not content:
            self._bus.publish(
                MEMORY_ERROR,
                {"message": "remember: use 'label | content' or 'label content...'"},
                source=self.name,
            )
            return
        payload: dict[str, object] = {
            "label": label,
            "content": content,
            "workspace_id": workspace_id,
            "entity_id": entity_id,
        }
        if global_search:
            payload["global_search"] = True
        self._on_remember(
            Event(
                topic=MEMORY_REMEMBER,
                payload=payload,
                source=self.name,
            )
        )

    def _handle_select_command(
        self,
        query: str,
        *,
        workspace_id: str = "",
        entity_id: str = "",
        global_search: bool = False,
    ) -> None:
        if not query:
            self._bus.publish(
                MEMORY_ERROR,
                {"message": "memory: requires a search query"},
                source=self.name,
            )
            return
        payload: dict[str, object] = {
            "query": query,
            "workspace_id": workspace_id,
            "entity_id": entity_id,
        }
        if global_search:
            payload["global_search"] = True
        self._on_select(
            Event(
                topic=MEMORY_SELECT,
                payload=payload,
                source=self.name,
            )
        )

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
