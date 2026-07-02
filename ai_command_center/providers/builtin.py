"""Built-in LLM provider descriptors (metadata only — HTTP in services)."""

from __future__ import annotations

from typing import Any

from ai_command_center.providers.llm_provider import LLMProvider, ProviderInfo

_OLLAMA_PREFIXES = ("llama", "mistral", "phi", "gemma", "qwen", "codellama", "deepseek")


class OllamaProviderDescriptor(LLMProvider):
    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="ollama",
            display_name="Ollama (local)",
            description="Local Ollama HTTP API",
            default_model="llama3.2:3b",
        )

    def supports(self, model: str) -> bool:
        lower = model.lower()
        if ":" in lower or lower.startswith(_OLLAMA_PREFIXES):
            return True
        return lower not in ("gpt-4", "gpt-4o", "gpt-3.5-turbo")

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.info.name,
            "display_name": self.info.display_name,
            "description": self.info.description,
            "default_model": self.info.default_model,
            "supports_streaming": self.info.supports_streaming,
        }


class OpenAIProviderDescriptor(LLMProvider):
    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="openai",
            display_name="OpenAI-compatible",
            description="OpenAI-compatible HTTP API (OpenAI, Groq, local proxies)",
            default_model="gpt-4o-mini",
        )

    def supports(self, model: str) -> bool:
        lower = model.lower()
        if lower.startswith(("gpt-", "o1", "o3", "claude", "mistral", "gemini")):
            return True
        return ":" not in lower

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.info.name,
            "display_name": self.info.display_name,
            "description": self.info.description,
            "default_model": self.info.default_model,
            "supports_streaming": self.info.supports_streaming,
        }
