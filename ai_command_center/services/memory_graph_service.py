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
)
from ai_command_center.db.memory_repository import MemoryRepository
from ai_command_center.services.base import BaseService
from ai_command_center.services.command_router_service import (
    INTENT_MEMORY_REMEMBER,
    INTENT_MEMORY_SELECT,
)


class MemoryGraphService(BaseService):
    name = "memory_graph"

    def __init__(self, bus, repo: MemoryRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._selected_snippets: list[str] = []
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
        if event.source != "command_router":
            return
        intent = event.payload.get("intent")
        args = event.payload.get("args") or {}
        if intent == INTENT_MEMORY_REMEMBER:
            self._handle_remember_command(str(args.get("body", "")))
        elif intent == INTENT_MEMORY_SELECT:
            self._handle_select_command(str(args.get("query", "")))

    def _handle_remember_command(self, body: str) -> None:
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
        self._on_remember(
            Event(
                topic=MEMORY_REMEMBER,
                payload={"label": label, "content": content},
                source=self.name,
            )
        )

    def _handle_select_command(self, query: str) -> None:
        if not query:
            self._bus.publish(
                MEMORY_ERROR,
                {"message": "memory: requires a search query"},
                source=self.name,
            )
            return
        self._on_select(
            Event(
                topic=MEMORY_SELECT,
                payload={"query": query},
                source=self.name,
            )
        )

    def _on_lookup_request(self, event: Event) -> None:
        query = str(event.payload.get("query", "")).strip()
        snippets: list[str] = []
        if query:
            nodes = self._repo.search(query)
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
        node_id = self._repo.remember(
            label=label,
            content=content,
            kind=str(event.payload.get("kind", "entity")),
            tier=str(event.payload.get("tier", "mid")),
            related_to=event.payload.get("related_to"),
            relation=str(event.payload.get("relation", "relates_to")),
        )
        self._bus.publish(
            MEMORY_STORED,
            {"id": node_id, "label": label},
            source=self.name,
        )

    def _on_select(self, event: Event) -> None:
        query = str(event.payload.get("query", "")).strip()
        node_id = str(event.payload.get("id", "")).strip()
        nodes = []
        if node_id:
            node = self._repo.get(node_id)
            if node:
                nodes = [node]
        elif query:
            nodes = self._repo.search(query)
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
