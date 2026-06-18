"""ARM64 gate, RAM detection, and Ollama reachability."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
OLLAMA_TIMEOUT_SEC = 5


def get_architecture() -> str:
    """Return platform.machine() normalized to upper case."""
    import platform

    return platform.machine().upper()


def is_arm64() -> bool:
    return get_architecture() == "ARM64"


def get_ram_mb() -> dict[str, float]:
    """Return total and available RAM in megabytes (and GB helpers)."""
    import psutil

    vm = psutil.virtual_memory()
    total_mb = vm.total / (1024 * 1024)
    avail_mb = vm.available / (1024 * 1024)
    return {
        "total_mb": round(total_mb, 1),
        "available_mb": round(avail_mb, 1),
        "total_gb": round(total_mb / 1024, 2),
        "available_gb": round(avail_mb / 1024, 2),
    }


def ollama_available() -> tuple[bool, str]:
    """Probe Ollama HTTP API. Returns (ok, detail_message)."""
    try:
        req = urllib.request.Request(OLLAMA_TAGS_URL, method="GET")
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SEC) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status != 200:
                return False, f"HTTP {resp.status}"
            try:
                data: Any = json.loads(body)
                models = data.get("models", [])
                return True, f"reachable ({len(models)} model(s) listed)"
            except json.JSONDecodeError:
                return True, "reachable (non-JSON response)"
    except urllib.error.URLError as exc:
        return False, str(exc.reason if hasattr(exc, "reason") else exc)
    except TimeoutError:
        return False, "connection timed out"
    except OSError as exc:
        return False, str(exc)
