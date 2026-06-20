"""Ollama service contract — Phase 3A interface + stub (no HTTP)."""

from __future__ import annotations

import uuid
from abc import abstractmethod

from ai_command_center.core.context_manager import ContextBundle
from ai_command_center.core.contracts import OLLAMA_SERVICE_API_VERSION
from ai_command_center.core.events.topics import (
    CHAT_CANCELLED,
    CHAT_CHUNK,
    CHAT_COMPLETE,
    CHAT_STARTED,
    OLLAMA_MODEL_LOADED,
    OLLAMA_MODEL_UNLOADED,
)
from ai_command_center.services.base import BaseService

# Stub response prefix — proves bundle reached Ollama layer without network.
_STUB_PREFIX = "[stub] "


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


class StubOllamaService(OllamaServiceBase):
    """Phase 3A stub — publishes chat.* events without network I/O."""

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._loaded_model: str | None = None
        self._active_request_id: str | None = None
        self._cancelled = False

    def _on_load(self) -> None:
        pass

    def load_model(self, model: str) -> None:
        self._loaded_model = model
        self._bus.publish(
            OLLAMA_MODEL_LOADED,
            {"model": model, "stub": True},
            source=self.name,
        )

    def unload_model(self) -> None:
        prev = self._loaded_model
        self._loaded_model = None
        if prev:
            self._bus.publish(
                OLLAMA_MODEL_UNLOADED,
                {"model": prev, "stub": True},
                source=self.name,
            )

    def stream_chat(
        self,
        bundle: ContextBundle,
        *,
        model: str,
        request_id: str | None = None,
    ) -> str:
        if not bundle.prompt:
            raise ValueError("ContextBundle.prompt must not be empty")

        rid = request_id or uuid.uuid4().hex
        self._active_request_id = rid
        self._cancelled = False

        self._bus.publish(
            CHAT_STARTED,
            {
                "request_id": rid,
                "model": model,
                "sources": list(bundle.sources),
                "token_estimate": bundle.token_estimate,
                "stub": True,
            },
            source=self.name,
        )

        response = f"{_STUB_PREFIX}Received {bundle.token_estimate} est. tokens from {len(bundle.sources)} source(s)."
        for i in range(0, len(response), 12):
            if self._cancelled:
                self._bus.publish(
                    CHAT_CANCELLED,
                    {"request_id": rid, "stub": True},
                    source=self.name,
                )
                self._active_request_id = None
                return rid
            chunk = response[i : i + 12]
            self._bus.publish(
                CHAT_CHUNK,
                {"request_id": rid, "text": chunk, "stub": True},
                source=self.name,
            )

        if self._cancelled:
            self._bus.publish(
                CHAT_CANCELLED,
                {"request_id": rid, "stub": True},
                source=self.name,
            )
        else:
            self._bus.publish(
                CHAT_COMPLETE,
                {
                    "request_id": rid,
                    "text": response,
                    "model": model,
                    "stub": True,
                },
                source=self.name,
            )

        self._active_request_id = None
        return rid

    def cancel(self, request_id: str | None = None) -> bool:
        if self._active_request_id is None:
            return False
        if request_id is not None and request_id != self._active_request_id:
            return False
        self._cancelled = True
        return True
