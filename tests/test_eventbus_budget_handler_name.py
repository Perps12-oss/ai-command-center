"""Budget warnings must name the slow handler (actionable observability)."""

from __future__ import annotations

import logging
import time

from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import UI_COMMAND


def test_budget_warning_includes_handler_qualname(caplog) -> None:
    bus = EventBus()

    def slow_ui_command(_event) -> None:
        # UI_COMMAND sync-critical budget is 5ms.
        time.sleep(0.02)

    bus.subscribe(UI_COMMAND, slow_ui_command)
    with caplog.at_level(logging.WARNING, logger="ai_command_center.core.event_bus"):
        bus.publish(UI_COMMAND, {"text": "ping"}, source="test")

    matching = [r for r in caplog.records if "exceeded budget" in r.getMessage()]
    assert matching, "expected a budget exceedance warning"
    message = matching[-1].getMessage()
    assert "handler=" in message
    assert "slow_ui_command" in message
