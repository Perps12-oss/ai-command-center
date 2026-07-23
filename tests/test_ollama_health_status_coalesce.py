"""Ollama health must fail fast and avoid redundant OLLAMA_STATUS publishes."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import OLLAMA_STATUS
from ai_command_center.services.ollama_http_service import OllamaHttpService


def test_health_check_publishes_once_for_stable_status() -> None:
    bus = EventBus()
    statuses: list[dict] = []
    bus.subscribe(OLLAMA_STATUS, lambda e: statuses.append(dict(e.payload)))

    service = OllamaHttpService(bus)
    resp = MagicMock()
    resp.status = 200
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.get = MagicMock(return_value=resp)
    service._session = session

    ticks = {"n": 0}

    async def fast_sleep(_seconds: float) -> None:
        ticks["n"] += 1
        if ticks["n"] >= 2:
            raise asyncio.CancelledError()

    async def run() -> None:
        with patch(
            "ai_command_center.services.ollama_http_service.asyncio.sleep",
            fast_sleep,
        ):
            # _health_check swallows CancelledError on sleep and exits cleanly.
            await service._health_check()

    asyncio.run(run())

    assert len(statuses) == 1
    assert statuses[0]["online"] is True
    assert session.get.call_count == 2


def test_health_timeouts_are_fail_fast() -> None:
    from ai_command_center.services import ollama_http_service as mod

    assert mod._HEALTH_TOTAL_TIMEOUT_S <= 2.0
    assert mod._HEALTH_CONNECT_TIMEOUT_S <= 1.0
    assert mod._HEALTH_TOTAL_TIMEOUT_S < mod._REQUEST_TIMEOUT_S
