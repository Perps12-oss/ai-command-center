"""Shared fixtures for service tests."""

from __future__ import annotations

import pytest

from ai_command_center.core.event_bus import EventBus


@pytest.fixture
def bus() -> EventBus:
    return EventBus()
