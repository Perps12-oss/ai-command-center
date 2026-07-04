"""Ollama service abstract base — shared by stub and HTTP implementations."""

from __future__ import annotations

from abc import abstractmethod

from ai_command_center.core.context_manager import ContextBundle
from ai_command_center.core.contracts import OLLAMA_SERVICE_API_VERSION
from ai_command_center.services.base import BaseService


class OllamaServiceBase(BaseService):
    """
    Contract for Ollama integration.

    Phase 3A: interface + StubOllamaService only.
    Phase 3B: real HTTP streaming implementation replaces stub.
    """

    name = "ollama"
    api_version = OLLAMA_SERVICE_API_VERSION

    @abstractmethod
    def load_model(self, model: str) -> None:
        """Ensure model is loaded (no-op in stub)."""

    @abstractmethod
    def unload_model(self) -> None:
        """Release loaded model (no-op in stub)."""

    @abstractmethod
    def stream_chat(
        self,
        bundle: ContextBundle,
        *,
        model: str,
        request_id: str | None = None,
    ) -> str:
        """
        Stream a chat completion from an assembled ContextBundle.

        Returns request_id for cancellation tracking.
        """

    @abstractmethod
    def cancel(self, request_id: str | None = None) -> bool:
        """Cancel in-flight stream; returns True if a stream was cancelled."""

    def stream(
        self,
        bundle: ContextBundle,
        *,
        model: str,
        request_id: str | None = None,
    ) -> str:
        """Contract v1.0 alias for stream_chat(bundle)."""
        return self.stream_chat(bundle, model=model, request_id=request_id)

    def chat(
        self,
        bundle: ContextBundle,
        *,
        model: str,
        request_id: str | None = None,
    ) -> str:
        """Contract v1.0 alias — streaming chat from ContextBundle."""
        return self.stream(bundle, model=model, request_id=request_id)


__all__ = ["OllamaServiceBase"]
