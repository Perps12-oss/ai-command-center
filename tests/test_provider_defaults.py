"""Tests for provider default helpers (F2 M2)."""

from __future__ import annotations

import unittest

from ai_command_center.providers.defaults import default_model_for_provider, provider_display_name


class ProviderDefaultsTests(unittest.TestCase):
    def test_openai_default_model(self) -> None:
        self.assertEqual(default_model_for_provider("openai"), "gpt-4o-mini")

    def test_ollama_default_model(self) -> None:
        self.assertEqual(default_model_for_provider("ollama"), "llama3.2:3b")

    def test_provider_display_name(self) -> None:
        self.assertIn("OpenAI", provider_display_name("openai"))


if __name__ == "__main__":
    unittest.main()
