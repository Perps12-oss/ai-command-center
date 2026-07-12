"""Stub model adapter for testing.

This adapter provides predictable responses for testing without
requiring external API access.
"""

from __future__ import annotations

from typing import Iterator

from ai_command_center.models.base import ModelAdapter, ModelConfig, ModelResponse
from ai_command_center.operator.mode_resolver import OperatorMode


class StubModelAdapter(ModelAdapter):
    """A stub adapter that returns predictable responses for testing."""

    name = "stub"

    def __init__(
        self,
        response_content: str = "Test response",
        model_name: str = "stub-model",
        supports_all_modes: bool = True,
        supported_modes: set[OperatorMode] | None = None,
    ) -> None:
        self._response_content = response_content
        self._model_name = model_name
        self._supports_all_modes = supports_all_modes
        self._supported_modes = supported_modes or {
            OperatorMode.CHAT,
            OperatorMode.COMMAND,
            OperatorMode.INVESTIGATION,
            OperatorMode.ARCHITECT,
        }
        self._call_count = 0
        self._last_prompt: str | None = None

    @property
    def supported_modes(self) -> set[OperatorMode]:
        return self._supported_modes

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def last_prompt(self) -> str | None:
        return self._last_prompt

    def complete(
        self,
        prompt: str,
        config: ModelConfig | None = None,
    ) -> ModelResponse:
        self._call_count += 1
        self._last_prompt = prompt

        return ModelResponse(
            content=self._response_content,
            model_name=self._model_name,
            finish_reason="stop",
            usage={
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(self._response_content.split()),
                "total_tokens": len(prompt.split()) + len(self._response_content.split()),
            },
            metadata={"adapter": "stub"},
        )

    def stream(
        self,
        prompt: str,
        config: ModelConfig | None = None,
    ) -> Iterator[ModelResponse]:
        self._call_count += 1
        self._last_prompt = prompt

        words = self._response_content.split()
        for i, word in enumerate(words):
            yield ModelResponse(
                content=word + (" " if i < len(words) - 1 else ""),
                model_name=self._model_name,
                finish_reason=None,
                usage={},
            )

        yield ModelResponse(
            content="",
            model_name=self._model_name,
            finish_reason="stop",
            usage={},
        )

    def health_check(self) -> bool:
        return True

    def reset(self) -> None:
        """Reset call count and last prompt."""
        self._call_count = 0
        self._last_prompt = None


class ConditionalStubAdapter(StubModelAdapter):
    """A stub adapter that returns different responses based on conditions."""

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        default_response: str = "Default response",
    ) -> None:
        super().__init__(response_content=default_response)
        self._responses = responses or {}
        self._default_response = default_response

    def complete(
        self,
        prompt: str,
        config: ModelConfig | None = None,
    ) -> ModelResponse:
        self._call_count += 1
        self._last_prompt = prompt

        # Check for matching condition in prompt
        for keyword, response in self._responses.items():
            if keyword.lower() in prompt.lower():
                return ModelResponse(
                    content=response,
                    model_name=self._model_name,
                    finish_reason="stop",
                    usage={},
                )

        return ModelResponse(
            content=self._default_response,
            model_name=self._model_name,
            finish_reason="stop",
            usage={},
        )


__all__ = ["ConditionalStubAdapter", "StubModelAdapter"]
