"""Locked two-tier Windows ARM64 native contract.

Core (Python process, Ollama PE, inference-critical wheels) must be native ARM64.
Named utility packages may ship AMD64 PE (Prism) on ARM64 Windows.

Keep scanner, wheel_audit, and docs in sync with this module.
"""

from __future__ import annotations

from pathlib import Path

# Inference / audio / vision — never allowlisted for emulation.
PERFORMANCE_CRITICAL_PACKAGES: frozenset[str] = frozenset(
    {
        "faster-whisper",
        "whisper",
        "openai-whisper",
        "tts",
        "screenpipe",
    }
)

# pip-normalized names whose AMD64 native extensions are permitted (owner 2026-08-16).
ALLOWLIST_EMULATION: frozenset[str] = frozenset(
    {
        "aiohttp",
        "yarl",
        "multidict",
        "frozenlist",
        "propcache",
        "watchdog",
        "pywin32",
        "psutil",
        "pyyaml",
        "pillow",
    }
)

# Directory / filename tokens used to map a PE path back to an allowlisted package.
_ALLOWLIST_PATH_TOKENS: frozenset[str] = frozenset(
    {
        "aiohttp",
        "yarl",
        "multidict",
        "frozenlist",
        "propcache",
        "watchdog",
        "psutil",
        "yaml",
        "pyyaml",
        "pil",
        "pillow",
        "win32",
        "win32com",
        "pythonwin",
        "pywin32_system32",
    }
)


def pip_allowlisted(pip_name: str) -> bool:
    return pip_name.lower() in ALLOWLIST_EMULATION


def is_allowlisted_emulation_path(path: Path | str) -> bool:
    """True when a PE file belongs to an allowlisted utility package."""
    p = Path(path)
    parts = [part.lower() for part in p.parts]
    if any(part in _ALLOWLIST_PATH_TOKENS for part in parts):
        return True
    name = p.name.lower()
    return name.startswith("pywintypes") or name.startswith("pythoncom")


def wheel_severity(
    arch: str,
    pip_name: str,
    *,
    critical: bool,
    perf_critical: bool,
) -> str:
    """Map wheel_audit classification to PASS/WARN/FAIL under two-tier policy."""
    name = pip_name.lower()
    if arch == "emulated_amd64":
        if name in ALLOWLIST_EMULATION:
            return "PASS"
        return "FAIL"
    if arch == "not_installed":
        return "FAIL" if critical else "WARN"
    if perf_critical and arch not in {"native_arm64", "pure_python"}:
        return "FAIL"
    return "PASS"
