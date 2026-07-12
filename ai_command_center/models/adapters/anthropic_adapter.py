"""Anthropic adapter — Claude API provider.

Reference: docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md Section 8.3
"""

from __future__ import annotations

import logging
import os
from typing import Any, Iterator

import httpx

from ai_command_center.models.base import ModelAdapter, ModelConfig, ModelResponse
from ai_command_center.operator.mode_resolver import OperatorMode

logger = logging.getLogger(__name__)


class AnthropicAdapter(ModelAdapter):
    """Adapter for Anthropic Claude API.

    Supports Claude models via the Anthropic Messages API.
    """

    name = "anthropic"

    # Anthropic API base URL
    ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "claude-3-sonnet-20240229",
        timeout: float = 120.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model_name = model_name
        self._timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def supported_modes(self) -> set[OperatorMode]:
        """Anthropic supports all standard modes."""
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
            self._client = httpx.Client(
                base_url=self.ANTHROPIC_BASE_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
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
        """Generate completion via Anthropic Messages API."""
        config = config or ModelConfig(model_name=self._model_name)

        payload: dict[str, Any] = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": min(config.max_tokens, 4096),  # Anthropic limit
        }

        if config.temperature > 0:
            payload["temperature"] = config.temperature

        if config.top_p < 1.0:
            payload["top_p"] = config.top_p

        if config.stop_sequences:
            payload["stop_sequences"] = config.stop_sequences

        try:
            client = self._get_client()
            response = client.post("/messages", json=payload)
            response.raise_for_status()
            data = response.json()

            content_blocks = data.get("content", [])
            # Get text content
            text_content = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    text_content = block.get("text", "")
                    break

            usage = data.get("usage", {})

            return ModelResponse(
                content=text_content,
                model_name=self._model_name,
                finish_reason=data.get("stop_reason"),
                usage={
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                },
            )

        except httpx.HTTPError as exc:
            logger.error("Anthropic request failed: %s", exc)
            raise

    def stream(
        self,
        prompt: str,
        config: ModelConfig | None = None,
    ) -> Iterator[ModelResponse]:
        """Stream completions via Anthropic Messages API."""
        config = config or ModelConfig(model_name=self._model_name)

        payload: dict[str, Any] = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": min(config.max_tokens, 4096),
            "stream": True,
        }

        if config.temperature > 0:
            payload["temperature"] = config.temperature

        try:
            client = self._get_client()
            with client.stream("POST", "/messages", json=payload) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

                    import json

                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    event_type = data.get("type")

                    if event_type == "content_block_delta":
                        delta = data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            content = delta.get("text", "")
                            if content:
                                yield ModelResponse(
                                    content=content,
                                    model_name=self._model_name,
                                    finish_reason=None,
                                    usage={},
                                )

                    elif event_type == "message_stop":
                        break

        except httpx.HTTPError as exc:
            logger.error("Anthropic stream failed: %s", exc)
            raise

    def health_check(self) -> bool:
        """Check if Anthropic API is accessible."""
        # Simple health check - make a minimal API call
        try:
            client = self._get_client()
            # Use a very short max_tokens to minimize cost
            response = client.post(
                "/messages",
                json={
                    "model": self._model_name,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                },
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False


__all__ = ["AnthropicAdapter"]
