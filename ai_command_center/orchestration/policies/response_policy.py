"""Response policy engine — routes classified intents before execution."""

from __future__ import annotations

from enum import Enum

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent

_ACTION_INTENTS = frozenset(
    {
        OrchestrationIntent.LAUNCH_APPLICATION,
        OrchestrationIntent.SEND_EMAIL,
        OrchestrationIntent.CALENDAR_EVENT_CREATE,
        OrchestrationIntent.EXECUTE_SHELL,
    }
)

_QUERY_INTENTS = frozenset(
    {
        OrchestrationIntent.SYSTEM_TIME_QUERY,
        OrchestrationIntent.CALENDAR_QUERY,
    }
)


class ResponsePolicy(str, Enum):
    """Runtime policy for how a classified intent should be handled."""

    ACTION = "action"
    QUERY = "query"
    DEFER_LLM = "defer_llm"
    UNSUPPORTED = "unsupported"


class ResponsePolicyEngine:
    """Determines orchestration policy from structured intent — no LLM."""

    @staticmethod
    def resolve(intent: OrchestrationIntent) -> ResponsePolicy:
        if intent in _ACTION_INTENTS:
            return ResponsePolicy.ACTION
        if intent in _QUERY_INTENTS:
            return ResponsePolicy.QUERY
        if intent is OrchestrationIntent.UNHANDLED:
            return ResponsePolicy.DEFER_LLM
        return ResponsePolicy.UNSUPPORTED

    @staticmethod
    def should_defer_to_llm(intent: OrchestrationIntent) -> bool:
        return ResponsePolicyEngine.resolve(intent) is ResponsePolicy.DEFER_LLM

    @staticmethod
    def requires_provider(intent: OrchestrationIntent) -> bool:
        return ResponsePolicyEngine.resolve(intent) in (
            ResponsePolicy.ACTION,
            ResponsePolicy.QUERY,
        )
