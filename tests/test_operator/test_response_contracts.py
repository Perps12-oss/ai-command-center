"""Tests for ResponseContracts."""

import pytest

from ai_command_center.operator.mode_resolver import OperatorMode
from ai_command_center.operator.response_contracts import (
    ArchitectResponse,
    Artifact,
    ChatResponse,
    CommandResponse,
    create_response,
    InvestigationResponse,
    Suggestion,
)


class TestChatResponse:
    """Tests for ChatResponse."""

    def test_basic_chat_response(self):
        """Basic chat response with message."""
        response = ChatResponse(message="Hello!")
        assert response.message == "Hello!"
        assert response.artifacts == []
        assert response.suggestions == []

    def test_chat_response_with_artifacts(self):
        """Chat response with code artifact."""
        response = ChatResponse(
            message="Here's the code:",
            artifacts=[
                Artifact(kind="code", content="print('hello')", language="python")
            ],
        )
        assert len(response.artifacts) == 1
        assert response.artifacts[0].language == "python"

    def test_chat_response_to_dict(self):
        """Chat response serializes correctly."""
        response = ChatResponse(message="Test")
        data = response.to_dict()
        assert data["type"] == "chat"
        assert data["message"] == "Test"

    def test_chat_response_validate_empty_message(self):
        """Validation fails for empty message."""
        response = ChatResponse(message="")
        errors = response.validate()
        assert "message is required" in errors


class TestCommandResponse:
    """Tests for CommandResponse."""

    def test_basic_command_response(self):
        """Basic command response."""
        response = CommandResponse(
            command="rm -rf /tmp/test",
            explanation="Removing test directory",
            confirm_required=True,
        )
        assert response.command == "rm -rf /tmp/test"
        assert response.confirm_required is True

    def test_command_response_to_dict(self):
        """Command response serializes correctly."""
        response = CommandResponse(
            command="git commit -m 'fix'",
            explanation="Creating commit",
        )
        data = response.to_dict()
        assert data["type"] == "command"
        assert data["command"] == "git commit -m 'fix'"
        assert data["confirm_required"] is True

    def test_command_response_validate_empty_command(self):
        """Validation fails for empty command."""
        response = CommandResponse(command="")
        errors = response.validate()
        assert "command is required" in errors

    def test_command_response_validate_missing_explanation(self):
        """Validation fails when confirm_required but no explanation."""
        response = CommandResponse(
            command="rm -rf /",
            confirm_required=True,
            explanation=None,
        )
        errors = response.validate()
        assert "explanation required when confirm_required is True" in errors


class TestInvestigationResponse:
    """Tests for InvestigationResponse."""

    def test_basic_investigation_response(self):
        """Basic investigation response."""
        response = InvestigationResponse(
            findings=["Bug found in line 42", "Null pointer exception"],
            confidence=0.8,
        )
        assert len(response.findings) == 2
        assert response.confidence == 0.8

    def test_investigation_response_to_dict(self):
        """Investigation response serializes correctly."""
        response = InvestigationResponse(
            findings=["Test finding"],
            confidence=0.5,
        )
        data = response.to_dict()
        assert data["type"] == "investigation"
        assert data["confidence"] == 0.5

    def test_investigation_response_validate_empty_findings(self):
        """Validation fails for empty findings."""
        response = InvestigationResponse(findings=[])
        errors = response.validate()
        assert "findings must not be empty" in errors

    def test_investigation_response_validate_invalid_confidence(self):
        """Validation fails for invalid confidence range."""
        response = InvestigationResponse(findings=["test"], confidence=1.5)
        errors = response.validate()
        assert any("confidence must be between" in e for e in errors)


class TestArchitectResponse:
    """Tests for ArchitectResponse."""

    def test_basic_architect_response(self):
        """Basic architect response."""
        response = ArchitectResponse(
            design="Use microservices architecture",
            risks=["Complexity", "Deployment overhead"],
        )
        assert "microservices" in response.design
        assert len(response.risks) == 2

    def test_architect_response_to_dict(self):
        """Architect response serializes correctly."""
        response = ArchitectResponse(design="Test design")
        data = response.to_dict()
        assert data["type"] == "architect"
        assert data["design"] == "Test design"

    def test_architect_response_validate_empty_design(self):
        """Validation fails for empty design."""
        response = ArchitectResponse(design="")
        errors = response.validate()
        assert "design is required" in errors


class TestCreateResponse:
    """Tests for create_response factory function."""

    def test_create_chat_response(self):
        """Creates ChatResponse for CHAT mode."""
        response = create_response(OperatorMode.CHAT, "Hello")
        assert isinstance(response, ChatResponse)
        assert response.message == "Hello"

    def test_create_command_response(self):
        """Creates CommandResponse for COMMAND mode."""
        response = create_response(OperatorMode.COMMAND, "ls -la")
        assert isinstance(response, CommandResponse)
        assert response.command == "ls -la"

    def test_create_investigation_response(self):
        """Creates InvestigationResponse for INVESTIGATION mode."""
        response = create_response(OperatorMode.INVESTIGATION, "Finding 1")
        assert isinstance(response, InvestigationResponse)
        assert "Finding 1" in response.findings

    def test_create_architect_response(self):
        """Creates ArchitectResponse for ARCHITECT mode."""
        response = create_response(OperatorMode.ARCHITECT, "Use service mesh")
        assert isinstance(response, ArchitectResponse)
        assert response.design == "Use service mesh"


class TestArtifactAndSuggestion:
    """Tests for Artifact and Suggestion dataclasses."""

    def test_artifact_creation(self):
        """Artifact can be created with all fields."""
        artifact = Artifact(
            kind="code",
            content="x = 1",
            language="python",
            filename="test.py",
        )
        assert artifact.kind == "code"
        assert artifact.language == "python"
        assert artifact.filename == "test.py"

    def test_suggestion_creation(self):
        """Suggestion can be created with all fields."""
        suggestion = Suggestion(
            label="Run tests",
            description="Execute pytest to verify the fix",
        )
        assert suggestion.label == "Run tests"
        assert "pytest" in suggestion.description
