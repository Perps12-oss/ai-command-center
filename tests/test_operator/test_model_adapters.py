"""Tests for model adapters."""

import pytest

from ai_command_center.models.adapters.stub_adapter import (
    ConditionalStubAdapter,
    StubModelAdapter,
)
from ai_command_center.models.base import ModelConfig, ModelResponse
from ai_command_center.operator.mode_resolver import OperatorMode


class TestStubModelAdapter:
    """Tests for StubModelAdapter."""

    def test_basic_complete(self):
        """Basic complete returns response."""
        adapter = StubModelAdapter(response_content="Test response")
        response = adapter.complete("test prompt")

        assert isinstance(response, ModelResponse)
        assert response.content == "Test response"
        assert response.model_name == "stub-model"

    def test_call_count_increments(self):
        """Call count increments on each complete."""
        adapter = StubModelAdapter(response_content="Test")

        assert adapter.call_count == 0
        adapter.complete("prompt 1")
        assert adapter.call_count == 1
        adapter.complete("prompt 2")
        assert adapter.call_count == 2

    def test_last_prompt_recorded(self):
        """Last prompt is recorded."""
        adapter = StubModelAdapter(response_content="Test")

        adapter.complete("first prompt")
        assert adapter.last_prompt == "first prompt"

        adapter.complete("second prompt")
        assert adapter.last_prompt == "second prompt"

    def test_supported_modes(self):
        """Stub supports all standard modes."""
        adapter = StubModelAdapter()

        assert OperatorMode.CHAT in adapter.supported_modes
        assert OperatorMode.COMMAND in adapter.supported_modes
        assert OperatorMode.INVESTIGATION in adapter.supported_modes
        assert OperatorMode.ARCHITECT in adapter.supported_modes

    def test_custom_supported_modes(self):
        """Custom supported modes can be set."""
        adapter = StubModelAdapter(
            supported_modes={OperatorMode.CHAT},
        )

        assert OperatorMode.CHAT in adapter.supported_modes
        assert OperatorMode.COMMAND not in adapter.supported_modes

    def test_stream(self):
        """Stream yields response chunks."""
        adapter = StubModelAdapter(response_content="Hello World")
        chunks = list(adapter.stream("test"))

        assert len(chunks) > 1
        # Last chunk should have finish_reason
        assert chunks[-1].finish_reason == "stop"

    def test_health_check(self):
        """Health check returns True."""
        adapter = StubModelAdapter()
        assert adapter.health_check() is True

    def test_reset(self):
        """Reset clears call count and last prompt."""
        adapter = StubModelAdapter(response_content="Test")

        adapter.complete("prompt")
        assert adapter.call_count == 1
        assert adapter.last_prompt == "prompt"

        adapter.reset()
        assert adapter.call_count == 0
        assert adapter.last_prompt is None


class TestConditionalStubAdapter:
    """Tests for ConditionalStubAdapter."""

    def test_conditional_response(self):
        """Conditional adapter returns matching response."""
        adapter = ConditionalStubAdapter(
            responses={
                "hello": "Hello back!",
                "goodbye": "See you later!",
            },
            default_response="I don't understand.",
        )

        response = adapter.complete("say hello to someone")
        assert response.content == "Hello back!"

        response = adapter.complete("time to say goodbye")
        assert response.content == "See you later!"

    def test_default_response(self):
        """Default response when no match."""
        adapter = ConditionalStubAdapter(
            responses={"hello": "Hi!"},
            default_response="Default",
        )

        response = adapter.complete("something else entirely")
        assert response.content == "Default"

    def test_case_insensitive(self):
        """Matching is case insensitive."""
        adapter = ConditionalStubAdapter(
            responses={"hello": "Hi!"},
            default_response="Default",
        )

        response = adapter.complete("HELLO there")
        assert response.content == "Hi!"


class TestModelConfig:
    """Tests for ModelConfig."""

    def test_default_config(self):
        """Default config has sensible values."""
        config = ModelConfig(model_name="test-model")

        assert config.model_name == "test-model"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.top_p == 1.0
        assert config.frequency_penalty == 0.0
        assert config.presence_penalty == 0.0
        assert config.stop_sequences == []

    def test_custom_config(self):
        """Custom config values are preserved."""
        config = ModelConfig(
            model_name="custom-model",
            temperature=0.5,
            max_tokens=2048,
            stop_sequences=["END"],
        )

        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert config.stop_sequences == ["END"]


class TestModelResponse:
    """Tests for ModelResponse."""

    def test_basic_response(self):
        """Basic response creation."""
        response = ModelResponse(
            content="Test content",
            model_name="test-model",
        )

        assert response.content == "Test content"
        assert response.model_name == "test-model"
        assert response.finish_reason is None
        assert response.usage == {}

    def test_full_response(self):
        """Full response with all fields."""
        response = ModelResponse(
            content="Full content",
            model_name="full-model",
            finish_reason="stop",
            usage={"tokens": 100},
            metadata={"key": "value"},
        )

        assert response.finish_reason == "stop"
        assert response.usage == {"tokens": 100}
        assert response.metadata == {"key": "value"}
