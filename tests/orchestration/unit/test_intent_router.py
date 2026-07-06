"""Layer 1 — IntentRouter unit tests (no providers/UI)."""

from __future__ import annotations

import pytest

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.routing.intent_router import IntentRouter


@pytest.mark.parametrize(
    ("intent", "expected_provider"),
    [
        (OrchestrationIntent.LAUNCH_APPLICATION, "application"),
        (OrchestrationIntent.SYSTEM_TIME_QUERY, "system_facts"),
        (OrchestrationIntent.CALENDAR_QUERY, "calendar"),
        (OrchestrationIntent.CALENDAR_EVENT_CREATE, "calendar"),
        (OrchestrationIntent.SEND_EMAIL, "email"),
    ],
)
def test_resolve_provider_maps_intents(
    intent: OrchestrationIntent,
    expected_provider: str,
) -> None:
    assert IntentRouter.resolve_provider(intent) == expected_provider


def test_unhandled_returns_empty_provider() -> None:
    assert IntentRouter.resolve_provider(OrchestrationIntent.UNHANDLED) == ""
