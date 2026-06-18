"""Opt-in memory graph — no background ingestion (Phase 4E)."""

from __future__ import annotations

from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.db.memory_repository import MemoryRepository
from ai_command_center.services.base import BaseService


class MemoryGraphService(BaseService):
    name = "memory_graph"

    def __init__(self, bus, repo: MemoryRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._selected_snippets: list[str] = []
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe("memory.remember", self._on_remember)
        )
        self._unsubscribers.append(
            self._bus.subscribe("memory.select", self._on_select)
        )
        self._unsubscribers.append(
            self._bus.subscribe("memory.clear_selection", self._on_clear)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()

    def get_context_snippets(self) -> list[str]:
        return list(self._selected_snippets)

    def _on_remember(self, event: Event) -> None:
        label = str(event.payload.get("label", "")).strip()
        content = str(event.payload.get("content", "")).strip()
        if not label or not content:
            self._bus.publish(
                "memory.error",
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
            "memory.stored",
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
                "memory.error",
                {"message": "no memory nodes matched selection"},
                source=self.name,
            )
            return
        self._selected_snippets = [
            f"[memory:{n.label}]\n{n.content}" for n in nodes[:3]
        ]
        self._bus.publish(
            "memory.selected",
            {"count": len(self._selected_snippets), "labels": [n.label for n in nodes[:3]]},
            source=self.name,
        )

    def _on_clear(self, _event: Event) -> None:
        self._selected_snippets.clear()
        self._bus.publish("memory.cleared", {}, source=self.name)
