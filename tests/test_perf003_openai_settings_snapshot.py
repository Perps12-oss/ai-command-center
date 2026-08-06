"""PERF-003: settings.snapshot must not hit keyring on the sync bus path."""

from __future__ import annotations

import time
from unittest.mock import patch

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import SETTINGS_SNAPSHOT
from ai_command_center.services.openai_http_service import OpenAIHttpService


def test_settings_snapshot_does_not_call_resolve_openai_api_key() -> None:
    """Delete keyring work from SYNC_CRITICAL settings.snapshot (PERF-003)."""
    bus = EventBus()
    service = OpenAIHttpService(bus)
    with patch(
        "ai_command_center.services.openai_http_service.resolve_openai_api_key",
        side_effect=AssertionError("resolve must not run on settings.snapshot"),
    ) as mocked:
        service._on_settings_snapshot(
            Event(
                topic=SETTINGS_SNAPSHOT,
                payload={
                    "provider": "openai",
                    "openai_base_url": "https://api.openai.com/v1",
                    "openai_api_key": "sk-from-settings",
                },
                source="test",
            )
        )
        mocked.assert_not_called()
    assert service._last_stored_api_key == "sk-from-settings"
    assert service._active_provider == "openai"


def test_settings_snapshot_handler_under_budget_without_keyring() -> None:
    bus = EventBus()
    service = OpenAIHttpService(bus)
    event = Event(
        topic=SETTINGS_SNAPSHOT,
        payload={
            "provider": "openai",
            "openai_base_url": "https://api.openai.com/v1",
            "openai_api_key": "********",
        },
        source="test",
    )
    # Cold path: first apply with distinct stored key (no resolve on path).
    times: list[float] = []
    for i in range(5):
        event = Event(
            topic=SETTINGS_SNAPSHOT,
            payload={
                "provider": "openai",
                "openai_base_url": "https://api.openai.com/v1",
                "openai_api_key": f"sk-{i}",
            },
            source="test",
        )
        st = time.perf_counter()
        service._on_settings_snapshot(event)
        times.append((time.perf_counter() - st) * 1000.0)
    assert max(times) < 5.0


def test_resolved_api_key_lazy_on_auth_headers() -> None:
    bus = EventBus()
    service = OpenAIHttpService(bus)
    service._last_stored_api_key = "sk-lazy"
    with patch(
        "ai_command_center.services.openai_http_service.resolve_openai_api_key",
        return_value="sk-resolved",
    ) as mocked:
        headers = service._auth_headers()
        mocked.assert_called_once_with("sk-lazy")
    assert headers["Authorization"] == "Bearer sk-resolved"


def test_identical_snapshot_early_returns() -> None:
    bus = EventBus()
    service = OpenAIHttpService(bus)
    payload = {
        "provider": "openai",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_api_key": "sk-a",
    }
    service._on_settings_snapshot(
        Event(topic=SETTINGS_SNAPSHOT, payload=payload, source="test")
    )
    with patch.object(service, "_resolved_api_key", wraps=service._resolved_api_key) as _:
        service._on_settings_snapshot(
            Event(topic=SETTINGS_SNAPSHOT, payload=dict(payload), source="test")
        )
    # Still only stored key from first apply; early return must not clear it.
    assert service._last_stored_api_key == "sk-a"
