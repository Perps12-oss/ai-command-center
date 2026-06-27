"""Phase 4 regression tests for ChatHandlerService reliability."""

from __future__ import annotations

import threading
import time
import unittest
from typing import Any

from ai_command_center.core.context_manager import ContextBundle, ContextManager
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    CHAT_CANCELLED,
    CHAT_ERROR,
    CHAT_STARTED,
    COMMAND_ROUTED,
    MEMORY_LOOKUP_REQUEST,
    MEMORY_LOOKUP_RESULT,
    MODEL_RESOLVE_REQUEST,
    MODEL_RESOLVE_RESULT,
    SESSION_HISTORY_REQUEST,
    SESSION_HISTORY_RESULT,
    UI_CHAT_CANCEL,
)
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.services.command_router_service import INTENT_CHAT
from ai_command_center.services.ollama_service import OllamaServiceBase


class _FakeOllamaService(OllamaServiceBase):
    """Ollama service stub that records stream calls and publishes CHAT_STARTED."""

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self.streams: list[tuple[ContextBundle, str, str]] = []

    def _on_load(self) -> None:
        pass

    def _on_unload(self) -> None:
        pass

    def load_model(self, model: str) -> None:
        pass

    def unload_model(self) -> None:
        pass

    def stream_chat(
        self,
        bundle: ContextBundle,
        *,
        model: str,
        request_id: str | None = None,
    ) -> str:
        rid = request_id or "no-request-id"
        self.streams.append((bundle, model, rid))
        self._bus.publish(
            CHAT_STARTED,
            {"request_id": rid},
            source=self.name,
        )
        return rid

    def cancel(self, request_id: str | None = None) -> bool:
        return False


class _EmptyPromptContextManager:
    """Context manager that always yields an empty prompt."""

    def __init__(self) -> None:
        self._budget = 100

    @property
    def context_budget_tokens(self) -> int:
        return self._budget

    def build_context(
        self,
        query: str,
        *,
        clipboard: str | None = None,
        notes: list[str] | None = None,
        graph_snippets: list[str] | None = None,
        conversation_history: list[tuple[str, str]] | None = None,
        clipboard_intent: bool = False,
    ) -> ContextBundle:
        return ContextBundle(prompt="", sources=(), token_estimate=0)


class _FakeUpstreamServices:
    """Responds to chat upstream requests with configurable delays."""

    def __init__(
        self,
        bus: EventBus,
        *,
        memory_delay: float = 0.0,
        history_delay: float = 0.0,
        model_delay: float = 0.0,
        memory_snippets: list[str] | None = None,
        history: list[tuple[str, str]] | None = None,
        model: str = "resolved-model",
    ) -> None:
        self._bus = bus
        self._memory_delay = memory_delay
        self._history_delay = history_delay
        self._model_delay = model_delay
        self._memory_snippets = memory_snippets or ["memory snippet"]
        self._history = history or [("user", "hi"), ("assistant", "hello")]
        self._model = model
        self._threads: list[threading.Thread] = []
        self._unsubs: list[Callable[[], None]] = []
        self._unsubs.append(bus.subscribe(MEMORY_LOOKUP_REQUEST, self._on_memory_request))
        self._unsubs.append(bus.subscribe(SESSION_HISTORY_REQUEST, self._on_history_request))
        self._unsubs.append(bus.subscribe(MODEL_RESOLVE_REQUEST, self._on_model_request))

    def unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        for t in self._threads:
            t.join(timeout=2.0)

    def _on_memory_request(self, event: Any) -> None:
        request_id = str(event.payload.get("request_id", ""))
        self._publish_after_delay(
            self._memory_delay,
            MEMORY_LOOKUP_RESULT,
            {"request_id": request_id, "snippets": self._memory_snippets},
        )

    def _on_history_request(self, event: Any) -> None:
        request_id = str(event.payload.get("request_id", ""))
        self._publish_after_delay(
            self._history_delay,
            SESSION_HISTORY_RESULT,
            {"request_id": request_id, "history": self._history},
        )

    def _on_model_request(self, event: Any) -> None:
        request_id = str(event.payload.get("request_id", ""))
        self._publish_after_delay(
            self._model_delay,
            MODEL_RESOLVE_RESULT,
            {"request_id": request_id, "model": self._model},
        )

    def _publish_after_delay(self, delay: float, topic: str, payload: dict[str, Any]) -> None:
        def _publish() -> None:
            if delay:
                time.sleep(delay)
            self._bus.publish(topic, payload, source="fake_upstream")

        t = threading.Thread(target=_publish, daemon=True)
        t.start()
        self._threads.append(t)


class ChatHandlerPhase4Tests(unittest.TestCase):
    def _make_handler(self, timeout: float = 0.1) -> tuple[EventBus, ChatHandlerService, _FakeOllamaService]:
        bus = EventBus()
        ollama = _FakeOllamaService(bus)
        context = ContextManager()
        handler = ChatHandlerService(bus, context, ollama, upstream_timeout_seconds=timeout)
        handler.load()
        ollama.load()
        return bus, handler, ollama

    def _route_chat(self, bus: EventBus, prompt: str = "hello") -> None:
        bus.publish(
            COMMAND_ROUTED,
            {
                "text": prompt,
                "intent": INTENT_CHAT,
                "args": {"prompt": prompt},
            },
            source="command_router",
        )

    def test_chat_error_includes_request_id_on_empty_prompt(self) -> None:
        """Every CHAT_ERROR from ChatHandler must carry the originating request_id."""
        bus = EventBus()
        ollama = _FakeOllamaService(bus)
        context = _EmptyPromptContextManager()
        handler = ChatHandlerService(bus, context, ollama, upstream_timeout_seconds=0.05)
        handler.load()

        errors: list[dict[str, Any]] = []
        bus.subscribe(CHAT_ERROR, lambda event: errors.append(dict(event.payload)))

        bus.publish(
            COMMAND_ROUTED,
            {
                "text": "test prompt",
                "intent": INTENT_CHAT,
                "args": {"prompt": "test prompt"},
            },
            source="command_router",
        )

        time.sleep(0.1)

        handler.unload()
        ollama.unload()

        self.assertEqual(1, len(errors))
        self.assertTrue(errors[0].get("request_id"))
        self.assertEqual("Empty prompt after context assembly", errors[0].get("message"))

    def test_synchronous_fast_path_uses_upstream_results(self) -> None:
        """When upstream services respond immediately, the chat streams with their results."""
        bus, handler, ollama = self._make_handler()
        upstream = _FakeUpstreamServices(bus)
        self._route_chat(bus)
        time.sleep(0.05)

        upstream.unload()
        handler.unload()
        ollama.unload()

        self.assertEqual(1, len(ollama.streams))
        bundle, model, _request_id = ollama.streams[0]
        self.assertEqual("resolved-model", model)
        self.assertIn("memory_graph_0", bundle.sources)

    def test_timeout_falls_back_to_default_model(self) -> None:
        """If model resolution is delayed past the timeout, the default model is used."""
        bus, handler, ollama = self._make_handler(timeout=0.1)
        upstream = _FakeUpstreamServices(bus, model_delay=0.5)
        self._route_chat(bus)
        time.sleep(0.2)

        upstream.unload()
        handler.unload()
        ollama.unload()

        self.assertEqual(1, len(ollama.streams))
        _bundle, model, _request_id = ollama.streams[0]
        self.assertEqual("llama3.2:3b", model)

    def test_timeout_falls_back_without_memory_snippets(self) -> None:
        """If memory lookup is delayed past the timeout, no snippets are injected."""
        bus, handler, ollama = self._make_handler(timeout=0.1)
        upstream = _FakeUpstreamServices(bus, memory_delay=0.5)
        self._route_chat(bus)
        time.sleep(0.2)

        upstream.unload()
        handler.unload()
        ollama.unload()

        self.assertEqual(1, len(ollama.streams))
        bundle, _model, _request_id = ollama.streams[0]
        self.assertNotIn("memory_graph_0", bundle.sources)

    def test_cancel_before_stream_start_emits_cancelled(self) -> None:
        """A UI cancel before upstream results arrive abandons the request."""
        bus, handler, ollama = self._make_handler(timeout=0.5)
        cancelled: list[dict[str, Any]] = []
        bus.subscribe(CHAT_CANCELLED, lambda event: cancelled.append(dict(event.payload)))

        # No upstream services are loaded, so the request will wait for the timeout.
        self._route_chat(bus)
        bus.publish(UI_CHAT_CANCEL, {}, source="ui")
        time.sleep(0.1)

        handler.unload()
        ollama.unload()

        self.assertEqual(0, len(ollama.streams))
        self.assertEqual(1, len(cancelled))
        self.assertTrue(cancelled[0].get("request_id"))


if __name__ == "__main__":
    unittest.main()
