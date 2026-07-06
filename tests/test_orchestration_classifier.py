"""Tests for rule-based orchestration intent classifier."""

from __future__ import annotations

from ai_command_center.orchestration.intents.classifier import RuleBasedIntentClassifier
from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent


def test_launch_application_intents() -> None:
    classifier = RuleBasedIntentClassifier()
    intent, args = classifier.classify("Open Outlook")
    assert intent is OrchestrationIntent.LAUNCH_APPLICATION
    assert args["application"] == "outlook"

    intent, args = classifier.classify("launch notepad")
    assert intent is OrchestrationIntent.LAUNCH_APPLICATION
    assert args["application"] == "notepad"


def test_system_time_query_intents() -> None:
    classifier = RuleBasedIntentClassifier()
    intent, _ = classifier.classify("What time is it?")
    assert intent is OrchestrationIntent.SYSTEM_TIME_QUERY

    intent, _ = classifier.classify("current time")
    assert intent is OrchestrationIntent.SYSTEM_TIME_QUERY


def test_calendar_query_intents() -> None:
    classifier = RuleBasedIntentClassifier()
    intent, _ = classifier.classify("What is on my calendar today?")
    assert intent is OrchestrationIntent.CALENDAR_QUERY


def test_unhandled_chat() -> None:
    classifier = RuleBasedIntentClassifier()
    intent, args = classifier.classify("Explain quantum computing")
    assert intent is OrchestrationIntent.UNHANDLED
    assert args == {}
