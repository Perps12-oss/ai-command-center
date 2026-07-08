"""Tests for orchestration request tracking registry."""

from __future__ import annotations

from ai_command_center.orchestration import orchestration_registry as registry


def test_orchestration_registry_tracks_and_clears_requests() -> None:
    registry.clear_orchestration_request("req-a")
    assert registry.is_orchestration_handled("req-a") is False
    registry.mark_orchestration_request("req-a")
    assert registry.is_orchestration_handled("req-a") is True
    registry.clear_orchestration_request("req-a")
    assert registry.is_orchestration_handled("req-a") is False


def test_orchestration_registry_evicts_oldest_when_bounded() -> None:
    original_max = registry._MAX_TRACKED_REQUESTS
    try:
        registry._MAX_TRACKED_REQUESTS = 2
        registry._orchestration_request_ids.clear()
        registry.mark_orchestration_request("req-1")
        registry.mark_orchestration_request("req-2")
        registry.mark_orchestration_request("req-3")
        assert registry.is_orchestration_handled("req-1") is False
        assert registry.is_orchestration_handled("req-2") is True
        assert registry.is_orchestration_handled("req-3") is True
    finally:
        registry._MAX_TRACKED_REQUESTS = original_max
        registry._orchestration_request_ids.clear()
