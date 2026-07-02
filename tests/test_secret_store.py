"""Tests for secure API key resolution (F2 M2)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from ai_command_center.platform.secret_store import (
    openai_api_key_configured,
    openai_api_key_source,
    resolve_openai_api_key,
    store_openai_api_key,
)


class SecretStoreTests(unittest.TestCase):
    def test_env_var_takes_precedence(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            self.assertEqual(resolve_openai_api_key("stored-key"), "env-key")
            self.assertEqual(openai_api_key_source("stored-key"), "env")

    def test_falls_back_to_stored_value(self) -> None:
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(resolve_openai_api_key("stored-key"), "stored-key")
            self.assertTrue(openai_api_key_configured("stored-key"))

    def test_store_empty_clears_without_keyring(self) -> None:
        stored = store_openai_api_key("")
        self.assertEqual(stored, "")


if __name__ == "__main__":
    unittest.main()
