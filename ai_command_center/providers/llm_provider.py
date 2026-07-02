"""Abstract LLM provider contract for multi-model foundation (F2 M1)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    """Metadata describing a registered LLM provider."""

    name: str
    display_name: str
    description: str
    default_model: str
    supports_streaming: bool = True


class LLMProvider(ABC):
    """Bus-native LLM provider contract — implementations subscribe to ``llm.request``."""

    @property
    @abstractmethod
    def info(self) -> ProviderInfo:
        """Return provider metadata."""

    @abstractmethod
    def supports(self, model: str) -> bool:
        """Return True when this provider can serve the given model name."""

    @abstractmethod
    def describe(self) -> dict[str, Any]:
        """Return a serializable provider description for diagnostics."""
