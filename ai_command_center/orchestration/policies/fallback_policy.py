"""Fallback policy when orchestration cannot proceed."""

from __future__ import annotations

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.policies.response_policy import ResponsePolicyEngine


class OrchestrationFallbackPolicy:
    """Determines whether orchestration should defer to LLM/capability routing."""

    @staticmethod
    def should_defer_to_llm(intent: OrchestrationIntent) -> bool:
        return ResponsePolicyEngine.should_defer_to_llm(intent)
