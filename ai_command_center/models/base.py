"""ModelAdapter — base contract for model providers.

Reference: docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md Section 8.3
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator

from ai_command_center.operator.mode_resolver import OperatorMode


@dataclass
class ModelConfig:
    """Configuration for model inference."""

    model_name: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: list[str] = field(default_factory=list)
    stream: bool = False
    timeout_seconds: float = 60.0


@dataclass
class ModelResponse:
    """Response from a model inference call."""

    content: str
    model_name: str
    finish_reason: str | None = None  # e.g., "stop", "length", "content_filter"
    usage: dict[str, int] = field(default_factory=dict)  # tokens used
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelAdapter(ABC):
    """Abstract base class for model providers.

    All adapters must implement the same interface regardless of provider.
    This ensures model independence - ACC behavior remains consistent
    across different model providers.

    Contract:
    - ACC never consumes raw model output directly
    - All output goes through ModelResponse contract
    - Providers translate to this contract internally
    """

    name: str = "base"

    @abstractmethod
    def complete(
        self,
        prompt: str,
        config: ModelConfig | None = None,
    ) -> ModelResponse:
        """Generate a completion for the given prompt.

        Args:
            prompt: The input prompt
            config: Optional inference configuration

        Returns:
            ModelResponse conforming to the contract
        """

    @abstractmethod
    def stream(
        self,
        prompt: str,
        config: ModelConfig | None = None,
    ) -> Iterator[ModelResponse]:
        """Stream completions for the given prompt.

        Args:
            prompt: The input prompt
            config: Optional inference configuration

        Yields:
            ModelResponse chunks as they arrive
        """

    @property
    @abstractmethod
    def supported_modes(self) -> set[OperatorMode]:
        """Return the operator modes this adapter supports."""

    @property
    def model_name(self) -> str:
        """Return the configured model name."""
        return getattr(self, "_model_name", "unknown")

    def health_check(self) -> bool:
        """Check if the model provider is available.

        Default implementation returns True.
        Override for provider-specific checks.
        """
        return True


__all__ = [
    "ModelAdapter",
    "ModelConfig",
    "ModelResponse",
]
