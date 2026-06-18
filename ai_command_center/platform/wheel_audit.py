"""Wheel architecture audit for Phase 0 preflight."""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

from ai_command_center.platform.detector import get_pe_machine_type

# Inference / AI / audio / vision — emulated x64 wheels are a hard fail.
PERFORMANCE_CRITICAL_PACKAGES: frozenset[str] = frozenset(
    {
        "faster-whisper",
        "whisper",
        "openai-whisper",
        "TTS",
        "screenpipe",
    }
)

# Phase 0 gate: must be importable before Phase 1.
CRITICAL_PHASE0_DEPS: list[tuple[str, str, str]] = [
    ("psutil", "psutil", "psutil"),
    ("pyyaml", "yaml", "pyyaml"),
]

# Full stack from requirements.txt — WARN if missing, not a Phase 0 hard fail.
OPTIONAL_DEPS: list[tuple[str, str, str]] = [
    ("customtkinter", "customtkinter", "customtkinter"),
    ("CTkMessagebox", "CTkMessagebox", "CTkMessagebox"),
    ("aiohttp", "aiohttp", "aiohttp"),
    ("mistune", "mistune", "mistune"),
    ("pystray", "pystray", "pystray"),
    ("Pillow", "PIL", "Pillow"),
    ("keyboard", "keyboard", "keyboard"),
    ("watchdog", "watchdog", "watchdog"),
    ("pywin32", "win32api", "pywin32"),
]


def _site_packages() -> list[Path]:
    return [Path(p) for p in sys.path if "site-packages" in p.replace("\\", "/")]


def _classify_extension(path: Path) -> str | None:
    name = path.name.lower()
    if "win_arm64" in name or "aarch64" in name:
        return "native_arm64"
    if "win_amd64" in name or "cp3" in name and "amd64" in name:
        return "emulated_amd64"
    if path.suffix.lower() in {".pyd", ".dll"}:
        machine = get_pe_machine_type(path)
        if machine == "ARM64":
            return "native_arm64"
        if machine == "AMD64":
            return "emulated_amd64"
    return None


def audit_wheel_arch(pip_name: str) -> tuple[str, str]:
    """
    Classify installed package binary architecture.
    Returns (classification, detail).
    """
    try:
        dist = importlib.metadata.distribution(pip_name)
    except importlib.metadata.PackageNotFoundError:
        return "not_installed", "package not installed"

    findings: list[tuple[str, str]] = []
    for file in dist.files or []:
        for site in _site_packages():
            full = site / str(file)
            if not full.is_file():
                continue
            kind = _classify_extension(full)
            if kind:
                findings.append((kind, full.name))

    if not findings:
        return "pure_python", "no native extension detected"

    if any(k == "native_arm64" for k, _ in findings):
        name = next(n for k, n in findings if k == "native_arm64")
        return "native_arm64", f"ARM64 binary: {name}"
    emulated = [n for k, n in findings if k == "emulated_amd64"]
    return "emulated_amd64", f"x64 binary (emulated on ARM): {emulated[0]}"


def audit_all_deps() -> list[dict[str, str]]:
    """Audit CRITICAL + OPTIONAL deps; return row dicts for reporting."""
    rows: list[dict[str, str]] = []
    for label, _import, pip_name in CRITICAL_PHASE0_DEPS + OPTIONAL_DEPS:
        arch, detail = audit_wheel_arch(pip_name)
        critical = pip_name.lower() in {p[2].lower() for p in CRITICAL_PHASE0_DEPS}
        perf_critical = pip_name.lower() in PERFORMANCE_CRITICAL_PACKAGES
        if arch == "emulated_amd64" and perf_critical:
            severity = "FAIL"
        elif arch == "emulated_amd64":
            severity = "WARN"
        elif arch == "not_installed" and critical:
            severity = "FAIL"
        elif arch == "not_installed":
            severity = "WARN"
        else:
            severity = "PASS"
        rows.append(
            {
                "package": label,
                "pip_name": pip_name,
                "arch": arch,
                "detail": detail,
                "severity": severity,
                "tier": "critical" if critical else "optional",
            }
        )
    return rows
