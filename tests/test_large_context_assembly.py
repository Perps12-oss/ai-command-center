"""Program 4 large-context acceptance tests."""

from __future__ import annotations

from typing import Any

from ai_command_center.core.capability_context_assembler import CapabilityContextAssembler
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
    WORKSPACE_CONTEXT_REQUEST,
    WORKSPACE_CONTEXT_RESULT,
)


class RecordingContextManager(ContextManager):
    def __init__(self, order: list[str]) -> None:
        super().__init__(max_context_tokens=1024)
        self._order = order
        self.graph_snippets: list[str] = []
        self.workspace_snippets: list[str] = []

    def build_context(self, query: str, **kwargs: Any):
        self._order.append("context_manager.build_context")
        self.graph_snippets = list(kwargs.get("graph_snippets") or [])
        self.workspace_snippets = list(kwargs.get("workspace_snippets") or [])
        return super().build_context(query, **kwargs)


def test_workspace_graph_context_resolves_before_context_manager_builds_prompt() -> None:
    bus = EventBus()
    order: list[str] = []

    bus.subscribe(
        MEMORY_LOOKUP_REQUEST,
        lambda e: bus.publish(
            MEMORY_LOOKUP_RESULT,
            {"request_id": e.payload["request_id"], "snippets": []},
            source="test",
        ),
    )
    bus.subscribe(
        SESSION_HISTORY_REQUEST,
        lambda e: bus.publish(
            SESSION_HISTORY_RESULT,
            {"request_id": e.payload["request_id"], "history": []},
            source="test",
        ),
    )

    def on_workspace_context(event) -> None:
        order.append("workspace.context.request")
        bus.publish(
            WORKSPACE_CONTEXT_RESULT,
            {
                "request_id": event.payload["request_id"],
                "snippets": ["Workspace graph: Alpha card contains Beta resource"],
            },
            source="test",
        )

    bus.subscribe(WORKSPACE_CONTEXT_REQUEST, on_workspace_context)
    manager = RecordingContextManager(order)
    assembler = CapabilityContextAssembler(bus, manager)

    assembled = assembler.assemble_for_command(
        request_id="req-large-context",
        query="summarize the workspace graph",
        event_payload={"workspace_id": "ws-large"},
        args={},
        source="test",
        include_model_resolve=False,
    )

    assert order == ["workspace.context.request", "context_manager.build_context"]
    assert manager.workspace_snippets == ["Workspace graph: Alpha card contains Beta resource"]
    assert "Workspace graph: Alpha card contains Beta resource" in assembled.bundle.prompt
    assert "workspace_state" in assembled.bundle.sources
