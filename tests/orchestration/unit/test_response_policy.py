"""Layer 1 — ResponsePolicyEngine unit tests (no providers/UI/LLM)."""

from __future__ import annotations

import pytest

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.policies.fallback_policy import OrchestrationFallbackPolicy
from ai_command_center.orchestration.policies.response_policy import ResponsePolicy, ResponsePolicyEngine


@pytest.mark.parametrize(
    ("intent", "expected_policy"),
    [
        (OrchestrationIntent.LAUNCH_APPLICATION, ResponsePolicy.ACTION),
        (OrchestrationIntent.SEND_EMAIL, ResponsePolicy.ACTION),
        (OrchestrationIntent.CALENDAR_EVENT_CREATE, ResponsePolicy.ACTION),
        (OrchestrationIntent.EXECUTE_SHELL, ResponsePolicy.ACTION),
        (OrchestrationIntent.SYSTEM_TIME_QUERY, ResponsePolicy.QUERY),
        (OrchestrationIntent.CALENDAR_QUERY, ResponsePolicy.QUERY),
        (OrchestrationIntent.UNHANDLED, ResponsePolicy.DEFER_LLM),
    ],
)
def test_resolve_policy(
    intent: OrchestrationIntent,
    expected_policy: ResponsePolicy,
) -> None:
    assert ResponsePolicyEngine.resolve(intent) is expected_policy


def test_should_defer_to_llm_only_for_unhandled() -> None:
    assert ResponsePolicyEngine.should_defer_to_llm(OrchestrationIntent.UNHANDLED) is True
    assert ResponsePolicyEngine.should_defer_to_llm(OrchestrationIntent.LAUNCH_APPLICATION) is False
    assert ResponsePolicyEngine.should_defer_to_llm(OrchestrationIntent.EXECUTE_SHELL) is False
    assert OrchestrationFallbackPolicy.should_defer_to_llm(OrchestrationIntent.UNHANDLED) is True


def test_requires_provider_for_action_and_query() -> None:
    assert ResponsePolicyEngine.requires_provider(OrchestrationIntent.LAUNCH_APPLICATION) is True
    assert ResponsePolicyEngine.requires_provider(OrchestrationIntent.CALENDAR_QUERY) is True
    assert ResponsePolicyEngine.requires_provider(OrchestrationIntent.EXECUTE_SHELL) is True
    assert ResponsePolicyEngine.requires_provider(OrchestrationIntent.UNHANDLED) is False
