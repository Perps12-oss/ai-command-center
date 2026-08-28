"""Secure resolution and storage for provider API keys and sidecar tokens.

Fail-closed: when the OS keyring cannot store a secret, ACC does not fall back
to plaintext SQLite. Env vars remain a supported source for headless/CI.
"""

from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

_SERVICE_NAME = "ai-command-center"
_OPENAI_KEY_NAME = "openai_api_key"
_OPENAI_ENV_VAR = "OPENAI_API_KEY"
_QWENPAW_TOKEN_NAME = "qwenpaw_auth_token"
_QWENPAW_ENV_VAR = "QWENPAW_AUTH_TOKEN"

_SECRET_MASK = "********"
_SECRET_PAYLOAD_KEYS = frozenset({"openai_api_key", "qwenpaw_auth_token"})

_keyring_module = None
_keyring_unavailable = False

_cache_lock = threading.Lock()
_resolved_cache: dict[str, str] = {}
_configured_cache: dict[str, bool] = {}
_qwenpaw_resolved_cache: dict[str, str] = {}
_qwenpaw_configured_cache: dict[str, bool] = {}


class SecretStoreError(RuntimeError):
    """Raised when a secret cannot be stored without plaintext persistence."""


def _cache_key(stored: str) -> str:
    return str(stored or "")


def invalidate_openai_key_cache() -> None:
    """Drop cached keyring/env resolutions (call after store/delete)."""
    with _cache_lock:
        _resolved_cache.clear()
        _configured_cache.clear()


def invalidate_qwenpaw_token_cache() -> None:
    with _cache_lock:
        _qwenpaw_resolved_cache.clear()
        _qwenpaw_configured_cache.clear()


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
            "keyring not installed; secrets require env vars (no plaintext settings fallback)"
        )
        return None
    except Exception:
        _keyring_unavailable = True
        logger.warning("keyring unavailable for secrets", exc_info=True)
        return None


def resolve_openai_api_key(stored: str = "") -> str:
    """Resolve OpenAI API key: env var → OS keyring → legacy settings (read-only)."""
    env = os.environ.get(_OPENAI_ENV_VAR, "").strip()
    if env:
        return env
    key = _cache_key(stored)
    with _cache_lock:
        cached = _resolved_cache.get(key)
        if cached is not None:
            return cached
    keyring = _get_keyring()
    if keyring is not None:
        try:
            value = keyring.get_password(_SERVICE_NAME, _OPENAI_KEY_NAME)
            if value:
                cleaned = value.strip()
                with _cache_lock:
                    _resolved_cache[key] = cleaned
                return cleaned
        except Exception:
            logger.warning("keyring read failed for OpenAI API key", exc_info=True)
    cleaned = str(stored or "").strip()
    if cleaned in {"", _SECRET_MASK}:
        cleaned = ""
    with _cache_lock:
        _resolved_cache[key] = cleaned
    return cleaned


def store_openai_api_key(value: str) -> str:
    """Persist API key in OS keyring only. Returns empty string for settings repo.

    Raises SecretStoreError when keyring cannot store a non-empty value (fail-closed).
    """
    invalidate_openai_key_cache()
    cleaned = str(value or "").strip()
    if cleaned in {_SECRET_MASK}:
        return ""
    keyring = _get_keyring()
    if not cleaned:
        if keyring is not None:
            try:
                keyring.delete_password(_SERVICE_NAME, _OPENAI_KEY_NAME)
            except Exception:
                logger.warning("keyring delete failed for OpenAI API key", exc_info=True)
        invalidate_openai_key_cache()
        return ""
    if keyring is None:
        raise SecretStoreError(
            "OS keyring unavailable; set OPENAI_API_KEY env or install keyring "
            "(refusing plaintext settings persistence)"
        )
    try:
        keyring.set_password(_SERVICE_NAME, _OPENAI_KEY_NAME, cleaned)
        invalidate_openai_key_cache()
        return ""
    except Exception as exc:
        invalidate_openai_key_cache()
        raise SecretStoreError(
            "keyring store failed; refusing plaintext settings persistence"
        ) from exc


def openai_api_key_configured(stored: str = "") -> bool:
    if os.environ.get(_OPENAI_ENV_VAR, "").strip():
        return True
    key = _cache_key(stored)
    with _cache_lock:
        cached = _configured_cache.get(key)
        if cached is not None:
            return cached
    result = bool(resolve_openai_api_key(stored))
    with _cache_lock:
        _configured_cache[key] = result
    return result


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
    if str(stored or "").strip() and str(stored).strip() != _SECRET_MASK:
        return "settings"
    return "none"


def resolve_qwenpaw_auth_token(stored: str = "") -> str:
    env = os.environ.get(_QWENPAW_ENV_VAR, "").strip()
    if env:
        return env
    key = _cache_key(stored)
    with _cache_lock:
        cached = _qwenpaw_resolved_cache.get(key)
        if cached is not None:
            return cached
    keyring = _get_keyring()
    if keyring is not None:
        try:
            value = keyring.get_password(_SERVICE_NAME, _QWENPAW_TOKEN_NAME)
            if value:
                cleaned = value.strip()
                with _cache_lock:
                    _qwenpaw_resolved_cache[key] = cleaned
                return cleaned
        except Exception:
            logger.warning("keyring read failed for QwenPaw auth token", exc_info=True)
    cleaned = str(stored or "").strip()
    if cleaned in {"", _SECRET_MASK}:
        cleaned = ""
    with _cache_lock:
        _qwenpaw_resolved_cache[key] = cleaned
    return cleaned


def store_qwenpaw_auth_token(value: str) -> str:
    invalidate_qwenpaw_token_cache()
    cleaned = str(value or "").strip()
    if cleaned in {_SECRET_MASK}:
        return ""
    keyring = _get_keyring()
    if not cleaned:
        if keyring is not None:
            try:
                keyring.delete_password(_SERVICE_NAME, _QWENPAW_TOKEN_NAME)
            except Exception:
                logger.warning("keyring delete failed for QwenPaw auth token", exc_info=True)
        invalidate_qwenpaw_token_cache()
        return ""
    if keyring is None:
        raise SecretStoreError(
            "OS keyring unavailable; set QWENPAW_AUTH_TOKEN env or install keyring "
            "(refusing plaintext settings persistence)"
        )
    try:
        keyring.set_password(_SERVICE_NAME, _QWENPAW_TOKEN_NAME, cleaned)
        invalidate_qwenpaw_token_cache()
        return ""
    except Exception as exc:
        invalidate_qwenpaw_token_cache()
        raise SecretStoreError(
            "keyring store failed; refusing plaintext settings persistence"
        ) from exc


def qwenpaw_auth_token_configured(stored: str = "") -> bool:
    if os.environ.get(_QWENPAW_ENV_VAR, "").strip():
        return True
    key = _cache_key(stored)
    with _cache_lock:
        cached = _qwenpaw_configured_cache.get(key)
        if cached is not None:
            return cached
    result = bool(resolve_qwenpaw_auth_token(stored))
    with _cache_lock:
        _qwenpaw_configured_cache[key] = result
    return result


def redact_settings_payload(payload: dict) -> dict:
    """Return a copy safe for EventBus / AppState projection."""
    out = dict(payload)
    for key in _SECRET_PAYLOAD_KEYS:
        if key not in out:
            continue
        raw = str(out.get(key) or "").strip()
        if not raw or raw == _SECRET_MASK:
            out[key] = ""
        else:
            # Opaque marker: configured-but-not-exported.
            out[key] = _SECRET_MASK
    return out


def bus_value_for_secret_key(key: str, value: object) -> object:
    if key not in _SECRET_PAYLOAD_KEYS:
        return value
    raw = str(value or "").strip()
    if not raw or raw == _SECRET_MASK:
        return ""
    return _SECRET_MASK
