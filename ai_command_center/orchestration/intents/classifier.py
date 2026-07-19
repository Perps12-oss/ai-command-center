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

_CREATE_EVENT_RE = re.compile(
    r"^\s*create\s+(?P<title>.+?)\s+(?:event\s+)?(?:today\s+)?(?:at\s+)?(?P<time>\d{1,2}:\d{2})\s*$",
    re.IGNORECASE,
)

# Shell verb prefixes that identify shell commands even without ">" prefix.
_SHELL_VERB_PREFIXES: tuple[str, ...] = (
    "echo ",
    "dir",
    "cd ",
    "ls ",
    "pwd",
    "whoami",
    "cat ",
    "type ",
    "python ",
    "git ",
    "node ",
    "npm ",
    "pip ",
    "get-childitem",
    "get-content ",
)


class RuleBasedIntentClassifier:
    """Classifies user text into orchestration intents using deterministic rules."""

    @staticmethod
    def classify(text: str) -> tuple[OrchestrationIntent, dict[str, str]]:
        normalized = text.strip()
        lower = normalized.lower()

        # Detect shell commands: ">" prefix or shell verb prefix
        if normalized.startswith(">"):
            command = normalized[1:].strip()
            return OrchestrationIntent.EXECUTE_SHELL, {"command": command}
        for prefix in _SHELL_VERB_PREFIXES:
            if lower.startswith(prefix.strip()):
                return OrchestrationIntent.EXECUTE_SHELL, {"command": normalized}

        match = _LAUNCH_RE.match(normalized)
        if match:
            app = match.group(1).lower()
            if app == "calc":
                app = "calculator"
            # Always actionable — unsupported apps fail at the provider/capability
            # layer with a receipt, never fall through to LLM.
            return OrchestrationIntent.LAUNCH_APPLICATION, {"application": app}

        if lower in _TIME_PHRASES or lower.rstrip("?") in _TIME_PHRASES:
            return OrchestrationIntent.SYSTEM_TIME_QUERY, {}

        for phrase in _CALENDAR_PHRASES:
            if phrase in lower:
                return OrchestrationIntent.CALENDAR_QUERY, {}

        create_match = _CREATE_EVENT_RE.match(normalized)
        if create_match:
            title = create_match.group("title").strip()
            event_time = create_match.group("time").strip()
            return OrchestrationIntent.CALENDAR_EVENT_CREATE, {
                "title": title,
                "time": event_time,
            }

        return OrchestrationIntent.UNHANDLED, {}
