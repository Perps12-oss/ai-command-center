"""Ollama adapter — local model provider.

Reference: docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md Section 8.3
"""

from __future__ import annotations

import logging
from typing import Any, Iterator

import httpx

from ai_command_center.models.base import ModelAdapter, ModelConfig, ModelResponse
from ai_command_center.operator.mode_resolver import OperatorMode

logger = logging.getLogger(__name__)


class OllamaAdapter(ModelAdapter):
    """Adapter for Ollama local models.

    Ollama provides local LLM inference with a REST API.
    See: https://github.com/ollama/ollama
    """

    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama2",
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name
        self._timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def supported_modes(self) -> set[OperatorMode]:
        """Ollama supports all standard modes."""
        return {
            OperatorMode.CHAT,
            OperatorMode.COMMAND,
            OperatorMode.INVESTIGATION,
            OperatorMode.ARCHITECT,
        }

    @property
    def model_name(self) -> str:
        return self._model_name

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=self._timeout)
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def complete(
        self,
        prompt: str,
        config: ModelConfig | None = None,
    ) -> ModelResponse:
        """Generate completion via Ollama API."""
        config = config or ModelConfig(model_name=self._model_name)

        # Build request payload
        payload: dict[str, Any] = {
            "model": config.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
            },
        }

        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences

        try:
            client = self._get_client()
            response = client.post(
                f"{self._base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            return ModelResponse(
                content=data.get("response", ""),
                model_name=self._model_name,
                finish_reason=data.get("done_reason"),
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                },
                metadata={
                    "total_duration": data.get("total_duration"),
                    "load_duration": data.get("load_duration"),
                },
            )

        except httpx.HTTPError as exc:
            logger.error("Ollama request failed: %s", exc)
            raise

    def stream(
        self,
        prompt: str,
        config: ModelConfig | None = None,
    ) -> Iterator[ModelResponse]:
        """Stream completions via Ollama API."""
        config = config or ModelConfig(model_name=self._model_name)

        payload: dict[str, Any] = {
            "model": config.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
            },
        }

        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences

        try:
            client = self._get_client()
            with client.stream(
                "POST",
                f"{self._base_url}/api/generate",
                json=payload,
            ) as response:
                response.raise_for_status()

                content_parts: list[str] = []

                for line in response.iter_lines():
                    if not line:
                        continue

                    import json

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    chunk = data.get("response", "")
                    content_parts.append(chunk)

                    yield ModelResponse(
                        content=chunk,
                        model_name=self._model_name,
                        finish_reason=data.get("done_reason"),
                        usage={},
                    )

                    if data.get("done"):
                        break

        except httpx.HTTPError as exc:
            logger.error("Ollama stream failed: %s", exc)
            raise

    def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            client = self._get_client()
            response = client.get(f"{self._base_url}/api/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False


__all__ = ["OllamaAdapter"]
