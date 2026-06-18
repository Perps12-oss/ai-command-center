"""ARM64 gate, RAM detection, Ollama reachability, and PE architecture probes."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
OLLAMA_TIMEOUT_SEC = 5

PE_MACHINE_AMD64 = 0x8664
PE_MACHINE_ARM64 = 0xAA64


def get_architecture() -> str:
    """Return platform.machine() normalized to upper case."""
    import platform

    return platform.machine().upper()


def is_arm64() -> bool:
    return get_architecture() == "ARM64"


def get_runtime_data_dir() -> Path:
    """Application data directory (not in repo)."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise OSError("APPDATA environment variable is not set")
    path = Path(appdata) / "AICommandCenter"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_baseline_log_path() -> Path:
    return get_runtime_data_dir() / "baseline.json"


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


def get_process_rss_mb() -> float:
    """RSS of the current Python process in megabytes."""
    import psutil

    return round(psutil.Process().memory_info().rss / (1024 * 1024), 1)


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


def get_pe_machine_type(exe_path: str | Path) -> str:
    """
    Read PE machine type from an executable.
    Returns ARM64, AMD64, or UNKNOWN.
    """
    path = Path(exe_path)
    if not path.is_file():
        return "UNKNOWN"
    try:
        data = path.read_bytes()
    except OSError:
        return "UNKNOWN"
    if len(data) < 64:
        return "UNKNOWN"
    e_lfanew = int.from_bytes(data[0x3C:0x40], "little")
    if e_lfanew + 6 > len(data):
        return "UNKNOWN"
    machine = int.from_bytes(data[e_lfanew + 4 : e_lfanew + 6], "little")
    if machine == PE_MACHINE_ARM64:
        return "ARM64"
    if machine == PE_MACHINE_AMD64:
        return "AMD64"
    return f"UNKNOWN_0x{machine:04X}"


def find_ollama_executable() -> Path | None:
    """Locate the main ollama.exe (not the tray helper)."""
    try:
        import psutil
    except ImportError:
        return None

    candidates: list[Path] = []
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            name = (proc.info.get("name") or "").lower()
            exe = proc.info.get("exe")
            if name == "ollama.exe" and exe:
                candidates.append(Path(exe))
        except (psutil.Error, OSError):
            continue

    if candidates:
        return candidates[0]

    default = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    if default.is_file():
        return default
    return None


def validate_ollama_arm64_native() -> tuple[bool, str]:
    """
    Hard gate: Ollama must be native ARM64 (PE machine type 0xAA64).
    HTTP reachability alone is not sufficient.
    """
    exe = find_ollama_executable()
    if exe is None:
        return False, "ollama.exe not found (install Ollama ARM64 or start the service)"

    machine = get_pe_machine_type(exe)
    if machine == "ARM64":
        return True, f"native ARM64 PE confirmed ({exe})"
    if machine == "AMD64":
        return False, f"x64/emulated AMD64 PE detected ({exe}) — install native ARM64 Ollama"
    return False, f"unable to verify ARM64 PE for {exe} (machine={machine})"


def write_baseline_log(
    *,
    package_import_ms: float | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Persist baseline RAM and startup metrics to %APPDATA%/AICommandCenter/baseline.json."""
    import sys

    ram = get_ram_mb()
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python": {
            "version": sys.version.split()[0],
            "executable": sys.executable,
            "machine": get_architecture(),
        },
        "ram": {
            **ram,
            "process_rss_mb": get_process_rss_mb(),
        },
        "startup": {},
    }
    if package_import_ms is not None:
        payload["startup"]["package_import_ms"] = round(package_import_ms, 2)
    if extra:
        payload.update(extra)

    path = get_baseline_log_path()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_baseline_log() -> dict[str, Any] | None:
    path = get_baseline_log_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
