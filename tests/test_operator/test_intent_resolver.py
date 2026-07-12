"""Tests for IntentResolver."""

import pytest

from ai_command_center.operator.intent_resolver import (
    IntentResolver,
    IntentType,
)


@pytest.fixture
def resolver(mock_event_bus):
    return IntentResolver(mock_event_bus)


class TestIntentResolver:
    """Tests for IntentResolver.resolve()"""

    def test_chat_intent_default(self, resolver):
        """Unclassifiable input defaults to chat intent."""
        intent = resolver.resolve("Hello, how are you?")
        assert intent.intent_type == IntentType.CHAT
        assert intent.confidence >= 0.5

    def test_command_intent_run(self, resolver):
        """'run' keyword triggers command intent."""
        intent = resolver.resolve("run the tests")
        assert intent.intent_type == IntentType.COMMAND
        assert "action_verb" in (intent.entities or {})

    def test_command_intent_create(self, resolver):
        """'create' keyword triggers command intent."""
        intent = resolver.resolve("create a new file")
        assert intent.intent_type == IntentType.COMMAND

    def test_command_intent_execute(self, resolver):
        """'execute' keyword triggers command intent."""
        intent = resolver.resolve("execute the deployment")
        assert intent.intent_type == IntentType.COMMAND

    def test_investigation_intent_find(self, resolver):
        """'find' keyword triggers investigation intent."""
        intent = resolver.resolve("find all memory leaks")
        assert intent.intent_type == IntentType.INVESTIGATION

    def test_investigation_intent_analyze(self, resolver):
        """'analyze' keyword triggers investigation intent."""
        intent = resolver.resolve("analyze this code")
        assert intent.intent_type == IntentType.INVESTIGATION

    def test_investigation_intent_trace(self, resolver):
        """'trace' keyword triggers investigation intent."""
        intent = resolver.resolve("trace the error")
        assert intent.intent_type == IntentType.INVESTIGATION

    def test_architect_intent_design(self, resolver):
        """'design' keyword triggers architect intent."""
        intent = resolver.resolve("design a new system")
        assert intent.intent_type == IntentType.ARCHITECT

    def test_architect_intent_propose(self, resolver):
        """'propose' keyword triggers architect intent."""
        intent = resolver.resolve("propose a solution")
        assert intent.intent_type == IntentType.ARCHITECT

    def test_memory_intent_remember(self, resolver):
        """'remember' keyword triggers memory intent."""
        intent = resolver.resolve("remember that I prefer dark mode")
        assert intent.intent_type == IntentType.MEMORY

    def test_settings_intent_configure(self, resolver):
        """'configure' keyword triggers settings intent."""
        intent = resolver.resolve("configure the theme")
        assert intent.intent_type == IntentType.SETTINGS

    def test_extracts_quoted_strings(self, resolver):
        """Quoted strings are extracted as entities."""
        intent = resolver.resolve('change "foo" to "bar"')
        assert "quoted_strings" in (intent.entities or {})
        assert "foo" in intent.entities["quoted_strings"]
        assert "bar" in intent.entities["quoted_strings"]

    def test_extracts_code_snippets(self, resolver):
        """Code snippets in backticks are extracted."""
        intent = resolver.resolve("explain `const x = 1`")
        assert "code_snippets" in (intent.entities or {})
        assert "const x = 1" in intent.entities["code_snippets"]
