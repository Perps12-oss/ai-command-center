"""Secure resolution and storage for provider API keys."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_SERVICE_NAME = "ai-command-center"
_OPENAI_KEY_NAME = "openai_api_key"
_OPENAI_ENV_VAR = "OPENAI_API_KEY"

_keyring_module = None
_keyring_unavailable = False


def _get_keyring():
    """Return the keyring module, or None when unavailable (logged once)."""
    global _keyring_module, _keyring_unavailable
    if _keyring_unavailable:
        return None
    if _keyring_module is not None:
        return _keyring_module
    try:
        import keyring as kr

        _keyring_module = kr
        return kr
    except ImportError:
        _keyring_unavailable = True
        logger.info(
            "keyring not installed; OpenAI API key will use env var or settings only"
        )
        return None
    except Exception:
        _keyring_unavailable = True
        logger.warning("keyring unavailable for OpenAI API key", exc_info=True)
        return None


def resolve_openai_api_key(stored: str = "") -> str:
    """Resolve OpenAI API key: env var → OS keyring → SQLite settings."""
    env = os.environ.get(_OPENAI_ENV_VAR, "").strip()
    if env:
        return env
    keyring = _get_keyring()
    if keyring is not None:
        try:
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
    keyring = _get_keyring()
    if keyring is None:
        return cleaned
    if not cleaned:
        try:
            keyring.delete_password(_SERVICE_NAME, _OPENAI_KEY_NAME)
        except Exception:
            logger.warning("keyring delete failed for OpenAI API key", exc_info=True)
        return ""
    try:
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
    keyring = _get_keyring()
    if keyring is not None:
        try:
            if keyring.get_password(_SERVICE_NAME, _OPENAI_KEY_NAME):
                return "keyring"
        except Exception:
            logger.warning("keyring probe failed for OpenAI API key source", exc_info=True)
    if str(stored or "").strip():
        return "settings"
    return "none"
