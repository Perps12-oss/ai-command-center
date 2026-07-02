"""Tests for multi-model provider foundation (F2 M1)."""

from __future__ import annotations

import unittest

from ai_command_center.providers.provider_registry import ProviderRegistry, build_default_registry


class ProviderRegistryTests(unittest.TestCase):
    def test_default_registry_lists_built_in_providers(self) -> None:
        registry = build_default_registry()
        names = registry.list_providers()
        self.assertIn("ollama", names)
        self.assertIn("openai", names)

    def test_describe_returns_metadata(self) -> None:
        registry = build_default_registry()
        info = registry.describe("openai")
        assert info is not None
        self.assertEqual(info["name"], "openai")
        self.assertIn("default_model", info)

    def test_resolve_for_model_prefers_configured_provider(self) -> None:
        registry = build_default_registry()
        resolved = registry.resolve_for_model("gpt-4o-mini", provider="openai")
        self.assertEqual(resolved, "openai")

    def test_ollama_supports_colon_models(self) -> None:
        registry = ProviderRegistry()
        from ai_command_center.providers.builtin import OllamaProviderDescriptor

        registry.register(OllamaProviderDescriptor())
        self.assertTrue(registry.get("ollama").supports("llama3.2:3b"))


if __name__ == "__main__":
    unittest.main()
