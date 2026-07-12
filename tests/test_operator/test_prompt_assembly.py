"""Tests for PromptAssemblyService."""

import pytest

from ai_command_center.operator.intent_resolver import Intent, IntentType
from ai_command_center.operator.mode_resolver import OperatorMode
from ai_command_center.operator.prompt_assembly import PromptAssemblyService


@pytest.fixture
def service(mock_event_bus):
    return PromptAssemblyService(mock_event_bus)


class TestPromptAssemblyService:
    """Tests for PromptAssemblyService.assemble()"""

    def test_assemble_includes_base_rules(self, service):
        """Assembled prompt includes base rules."""
        prompt = service.assemble(
            mode=OperatorMode.CHAT,
            intent=Intent(IntentType.CHAT, 0.8),
            user_input="Hello",
        )
        assert "You are an AI Command Center operator" in prompt

    def test_assemble_includes_mode_rules(self, service):
        """Assembled prompt includes mode-specific rules."""
        prompt = service.assemble(
            mode=OperatorMode.COMMAND,
            intent=Intent(IntentType.COMMAND, 0.9),
            user_input="run tests",
        )
        assert "COMMAND MODE RULES" in prompt
        assert "actionable commands" in prompt

    def test_assemble_includes_workspace_context(self, service):
        """Assembled prompt includes workspace state."""
        workspace = {
            "workspace_name": "test-project",
            "workspace_path": "/home/user/project",
            "context_type": "code_review",
        }
        prompt = service.assemble(
            mode=OperatorMode.CHAT,
            intent=Intent(IntentType.CHAT, 0.8),
            user_input="review this",
            workspace_context=workspace,
        )
        assert "WORKSPACE STATE" in prompt
        assert "test-project" in prompt

    def test_assemble_includes_conversation_history(self, service):
        """Assembled prompt includes recent conversation."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]
        prompt = service.assemble(
            mode=OperatorMode.CHAT,
            intent=Intent(IntentType.CHAT, 0.8),
            user_input="Good",
            conversation_history=history,
        )
        assert "CONVERSATION HISTORY" in prompt
        assert "Hello" in prompt
        assert "How are you?" in prompt

    def test_assemble_limits_history_to_five_turns(self, service):
        """History is limited to last 5 turns."""
        history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(10)
        ]
        prompt = service.assemble(
            mode=OperatorMode.CHAT,
            intent=Intent(IntentType.CHAT, 0.8),
            user_input="Latest",
            conversation_history=history,
        )
        assert "Message 0" not in prompt  # Should be truncated
        assert "Message 9" in prompt  # Most recent should be included

    def test_assemble_includes_evidence(self, service):
        """Assembled prompt includes evidence layer."""
        evidence = [
            "File tests/test_example.py exists",
            "Function foo() returns None",
        ]
        prompt = service.assemble(
            mode=OperatorMode.INVESTIGATION,
            intent=Intent(IntentType.INVESTIGATION, 0.8),
            user_input="Analyze this",
            evidence=evidence,
        )
        assert "EVIDENCE" in prompt
        assert "tests/test_example.py" in prompt
        assert "foo()" in prompt

    def test_assemble_includes_user_request(self, service):
        """Assembled prompt includes user request."""
        prompt = service.assemble(
            mode=OperatorMode.CHAT,
            intent=Intent(IntentType.CHAT, 0.8),
            user_input="What is the meaning of life?",
        )
        assert "USER REQUEST" in prompt
        assert "What is the meaning of life?" in prompt

    def test_assemble_command_mode_rules(self, service):
        """Command mode has correct rules."""
        prompt = service.assemble(
            mode=OperatorMode.COMMAND,
            intent=Intent(IntentType.COMMAND, 0.9),
            user_input="install package",
        )
        assert "COMMAND MODE RULES" in prompt
        assert "rollback" in prompt.lower()

    def test_assemble_investigation_mode_rules(self, service):
        """Investigation mode has correct rules."""
        prompt = service.assemble(
            mode=OperatorMode.INVESTIGATION,
            intent=Intent(IntentType.INVESTIGATION, 0.9),
            user_input="find bugs",
        )
        assert "INVESTIGATION MODE RULES" in prompt
        assert "evidence" in prompt.lower()
        assert "confidence" in prompt.lower()

    def test_assemble_architect_mode_rules(self, service):
        """Architect mode has correct rules."""
        prompt = service.assemble(
            mode=OperatorMode.ARCHITECT,
            intent=Intent(IntentType.ARCHITECT, 0.9),
            user_input="design system",
        )
        assert "ARCHITECT MODE RULES" in prompt
        assert "tradeoffs" in prompt.lower()
        assert "risks" in prompt.lower()
