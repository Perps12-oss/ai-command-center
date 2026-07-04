"""Secure resolution and storage for provider API keys."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_SERVICE_NAME = "ai-command-center"
_OPENAI_KEY_NAME = "openai_api_key"
_OPENAI_ENV_VAR = "OPENAI_API_KEY"


def resolve_openai_api_key(stored: str = "") -> str:
    """Resolve OpenAI API key: env var → OS keyring → SQLite settings."""
    env = os.environ.get(_OPENAI_ENV_VAR, "").strip()
    if env:
        return env
    try:
        import keyring

        value = keyring.get_password(_SERVICE_NAME, _OPENAI_KEY_NAME)
        if value:
            return value.strip()
    except Exception:
        logger.warning("keyring read failed for OpenAI API key", exc_info=True)
    cleaned = str(stored or "").strip()
    if cleaned in {"", "********"}:
        return ""
    return cleaned


def store_openai_api_key(value: str) -> str:
    """Persist API key off SQLite when possible; return value for settings repo."""
    cleaned = str(value or "").strip()
    if not cleaned:
        try:
            import keyring

            keyring.delete_password(_SERVICE_NAME, _OPENAI_KEY_NAME)
        except Exception:
            logger.warning("keyring delete failed for OpenAI API key", exc_info=True)
        return ""
    try:
        import keyring

        keyring.set_password(_SERVICE_NAME, _OPENAI_KEY_NAME, cleaned)
        return ""
    except Exception:
        logger.warning(
            "keyring store failed; persisting OpenAI API key in settings (plaintext fallback)",
            exc_info=True,
        )
        return cleaned


def openai_api_key_configured(stored: str = "") -> bool:
    return bool(resolve_openai_api_key(stored))


def openai_api_key_source(stored: str = "") -> str:
    """Return where the active key comes from: env, keyring, settings, or none."""
    if os.environ.get(_OPENAI_ENV_VAR, "").strip():
        return "env"
    try:
        import keyring

        if keyring.get_password(_SERVICE_NAME, _OPENAI_KEY_NAME):
            return "keyring"
    except Exception:
        logger.warning("keyring probe failed for OpenAI API key source", exc_info=True)
    if str(stored or "").strip():
        return "settings"
    return "none"
