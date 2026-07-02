"""OpenAI LLM bus integration test with mocked SSE (F2 M2)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from ai_command_center.core.context_manager import ContextBundle
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import CHAT_CHUNK, CHAT_COMPLETE, CHAT_STARTED
from ai_command_center.services.openai_http_service import OpenAIHttpService


class _FakeStreamResponse:
    def __init__(self, lines: list[bytes]) -> None:
        self.status = 200
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        return None

    @property
    def content(self):
        async def _iter():
            for line in self._lines:
                yield line

        return _iter()

    async def text(self) -> str:
        return ""


class OpenAILLMBusTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_publishes_bus_events(self) -> None:
        bus = EventBus(debug_mode=True)
        topics: list[str] = []
        payloads: dict[str, dict] = {}

        def tap(event) -> None:
            topics.append(event.topic)
            payloads[event.topic] = dict(event.payload)

        bus.subscribe_all(tap)

        service = OpenAIHttpService(bus)
        service._base_url = "https://api.test/v1"
        service._api_key = "sk-test"
        service._session = MagicMock()

        sse_lines = [
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
            b"data: [DONE]\n",
        ]
        fake_resp = _FakeStreamResponse(sse_lines)
        service._session.post = MagicMock(return_value=fake_resp)

        bundle = ContextBundle(
            prompt="Say hello",
            sources=(),
            token_estimate=10,
        )
        await service._stream_chat_async(bundle, "gpt-4o-mini", "req-1")

        self.assertIn(CHAT_STARTED, topics)
        self.assertIn(CHAT_CHUNK, topics)
        self.assertIn(CHAT_COMPLETE, topics)
        self.assertEqual(payloads[CHAT_COMPLETE]["text"], "Hello")


if __name__ == "__main__":
    unittest.main()
