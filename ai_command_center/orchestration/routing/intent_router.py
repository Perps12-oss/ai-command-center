"""Maps orchestration intents to provider identifiers."""

from __future__ import annotations

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent

_INTENT_PROVIDER: dict[OrchestrationIntent, str] = {
    OrchestrationIntent.LAUNCH_APPLICATION: "application",
    OrchestrationIntent.SYSTEM_TIME_QUERY: "system_facts",
    OrchestrationIntent.CALENDAR_QUERY: "calendar",
    OrchestrationIntent.CALENDAR_EVENT_CREATE: "calendar",
    OrchestrationIntent.SEND_EMAIL: "email",
    OrchestrationIntent.EXECUTE_SHELL: "shell",
}


class IntentRouter:
    """Selects the orchestration provider for a classified intent."""

    @staticmethod
    def resolve_provider(intent: OrchestrationIntent) -> str:
        if intent is OrchestrationIntent.UNHANDLED:
            return ""
        return _INTENT_PROVIDER.get(intent, "")
