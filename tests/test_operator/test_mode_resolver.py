"""Tests for ModeResolver."""

import pytest

from ai_command_center.operator.intent_resolver import Intent, IntentType
from ai_command_center.operator.mode_resolver import ModeResolver, OperatorMode


@pytest.fixture
def resolver(mock_event_bus):
    return ModeResolver(mock_event_bus)


class TestModeResolver:
    """Tests for ModeResolver.resolve()"""

    def test_chat_intent_maps_to_chat_mode(self, resolver):
        """CHAT intent resolves to CHAT mode."""
        intent = Intent(IntentType.CHAT, 0.8)
        mode = resolver.resolve(intent, "Hello, how are you?")
        assert mode == OperatorMode.CHAT

    def test_command_intent_maps_to_command_mode(self, resolver):
        """COMMAND intent resolves to COMMAND mode."""
        intent = Intent(IntentType.COMMAND, 0.9)
        mode = resolver.resolve(intent, "run the tests")
        assert mode == OperatorMode.COMMAND

    def test_investigation_intent_maps_to_investigation_mode(self, resolver):
        """INVESTIGATION intent resolves to INVESTIGATION mode."""
        intent = Intent(IntentType.INVESTIGATION, 0.9)
        mode = resolver.resolve(intent, "find all bugs")
        assert mode == OperatorMode.INVESTIGATION

    def test_architect_intent_maps_to_architect_mode(self, resolver):
        """ARCHITECT intent resolves to ARCHITECT mode."""
        intent = Intent(IntentType.ARCHITECT, 0.9)
        mode = resolver.resolve(intent, "design a new system")
        assert mode == OperatorMode.ARCHITECT

    def test_explicit_investigate_overrides_intent(self, resolver):
        """Explicit 'investigate' in input overrides intent mapping."""
        intent = Intent(IntentType.CHAT, 0.5)
        mode = resolver.resolve(intent, "investigate this issue")
        assert mode == OperatorMode.INVESTIGATION

    def test_explicit_analyze_this_overrides_intent(self, resolver):
        """Explicit 'analyze this' in input overrides intent mapping."""
        intent = Intent(IntentType.CHAT, 0.5)
        mode = resolver.resolve(intent, "analyze this code")
        assert mode == OperatorMode.INVESTIGATION

    def test_explicit_design_overrides_intent(self, resolver):
        """Explicit 'design' in input overrides intent mapping."""
        intent = Intent(IntentType.COMMAND, 0.5)
        mode = resolver.resolve(intent, "design a solution")
        assert mode == OperatorMode.ARCHITECT

    def test_context_override_code_review(self, resolver):
        """Code review context prefers investigation mode."""
        intent = Intent(IntentType.CHAT, 0.5)
        mode = resolver.resolve(
            intent,
            "review this",
            workspace_context={"context_type": "code_review"},
        )
        assert mode == OperatorMode.INVESTIGATION

    def test_context_override_design(self, resolver):
        """Design context prefers architect mode."""
        intent = Intent(IntentType.CHAT, 0.5)
        mode = resolver.resolve(
            intent,
            "suggest improvements",
            workspace_context={"context_type": "design"},
        )
        assert mode == OperatorMode.ARCHITECT

    def test_get_mode_contract_chat(self, resolver):
        """CHAT mode returns ChatResponse contract."""
        contract = resolver.get_mode_contract(OperatorMode.CHAT)
        assert contract == "ChatResponse"

    def test_get_mode_contract_command(self, resolver):
        """COMMAND mode returns CommandResponse contract."""
        contract = resolver.get_mode_contract(OperatorMode.COMMAND)
        assert contract == "CommandResponse"

    def test_get_mode_contract_investigation(self, resolver):
        """INVESTIGATION mode returns InvestigationResponse contract."""
        contract = resolver.get_mode_contract(OperatorMode.INVESTIGATION)
        assert contract == "InvestigationResponse"

    def test_get_mode_contract_architect(self, resolver):
        """ARCHITECT mode returns ArchitectResponse contract."""
        contract = resolver.get_mode_contract(OperatorMode.ARCHITECT)
        assert contract == "ArchitectResponse"
