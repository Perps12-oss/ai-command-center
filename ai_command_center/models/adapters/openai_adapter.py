"""OpenAI adapter — OpenAI API provider.

Reference: docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md Section 8.3
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Iterator

import httpx

from ai_command_center.models.base import ModelAdapter, ModelConfig, ModelResponse
from ai_command_center.operator.mode_resolver import OperatorMode

logger = logging.getLogger(__name__)


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI API.

    Supports both OpenAI and Azure OpenAI endpoints.
    """

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        model_name: str = "gpt-4",
        organization: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name
        self._organization = organization
        self._timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def supported_modes(self) -> set[OperatorMode]:
        """OpenAI supports all standard modes."""
        return {
            OperatorMode.CHAT,
            OperatorMode.COMMAND,
            OperatorMode.INVESTIGATION,
            OperatorMode.ARCHITECT,
        }

    @property
    def model_name(self) -> str:
        return self._model_name

    def _get_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._organization:
            headers["OpenAI-Organization"] = self._organization
        return headers

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self._base_url,
                headers=self._get_headers(),
                timeout=self._timeout,
            )
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
        """Generate completion via OpenAI Chat API."""
        config = config or ModelConfig(model_name=self._model_name)

        payload: dict[str, Any] = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
        }

        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        try:
            client = self._get_client()
            response = client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            message = choice["message"]
            usage = data.get("usage", {})

            return ModelResponse(
                content=message.get("content", ""),
                model_name=self._model_name,
                finish_reason=choice.get("finish_reason"),
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            )

        except httpx.HTTPError as exc:
            logger.error("OpenAI request failed: %s", exc)
            raise

    def stream(
        self,
        prompt: str,
        config: ModelConfig | None = None,
    ) -> Iterator[ModelResponse]:
        """Stream completions via OpenAI Chat API."""
        config = config or ModelConfig(model_name=self._model_name)

        payload: dict[str, Any] = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "stream": True,
        }

        if config.stop_sequences:
            payload["stop"] = config.stop_sequences

        try:
            client = self._get_client()
            with client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choice = data["choices"][0]
                    delta = choice.get("delta", {})
                    content = delta.get("content", "")

                    if content:
                        yield ModelResponse(
                            content=content,
                            model_name=self._model_name,
                            finish_reason=None,
                            usage={},
                        )

                    if choice.get("finish_reason"):
                        break

        except httpx.HTTPError as exc:
            logger.error("OpenAI stream failed: %s", exc)
            raise

    def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            client = self._get_client()
            response = client.get("/models")
            return response.status_code == 200
        except httpx.HTTPError:
            return False


__all__ = ["OpenAIAdapter"]
