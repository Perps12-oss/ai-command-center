"""Rule-based intent classifier — no LLM."""

from __future__ import annotations

import re

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent

_LAUNCH_RE = re.compile(
    r"^\s*(?:open|launch|start)\s+(\w+)\s*$",
    re.IGNORECASE,
)
_LAUNCH_APPS = frozenset({"outlook", "notepad", "calculator", "calc"})

_TIME_PHRASES: tuple[str, ...] = (
    "what time is it",
    "what's the time",
    "whats the time",
    "current time",
    "tell me the time",
)

_CALENDAR_PHRASES: tuple[str, ...] = (
    "what is on my calendar",
    "what's on my calendar",
    "whats on my calendar",
    "what do i have on my calendar",
    "show my calendar",
)


class RuleBasedIntentClassifier:
    """Classifies user text into orchestration intents using deterministic rules."""

    @staticmethod
    def classify(text: str) -> tuple[OrchestrationIntent, dict[str, str]]:
        normalized = text.strip()
        lower = normalized.lower()

        match = _LAUNCH_RE.match(normalized)
        if match:
            app = match.group(1).lower()
            if app == "calc":
                app = "calculator"
            if app in _LAUNCH_APPS:
                return OrchestrationIntent.LAUNCH_APPLICATION, {"application": app}

        if lower in _TIME_PHRASES or lower.rstrip("?") in _TIME_PHRASES:
            return OrchestrationIntent.SYSTEM_TIME_QUERY, {}

        for phrase in _CALENDAR_PHRASES:
            if phrase in lower:
                return OrchestrationIntent.CALENDAR_QUERY, {}

        return OrchestrationIntent.UNHANDLED, {}
