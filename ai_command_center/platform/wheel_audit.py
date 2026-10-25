"""Wheel architecture audit for Phase 0 preflight (two-tier ARM64 contract)."""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

from ai_command_center.platform.arm64_policy import (
    ALLOWLIST_EMULATION,
    PERFORMANCE_CRITICAL_PACKAGES,
    pip_allowlisted,
    wheel_severity,
)
from ai_command_center.platform.detector import get_pe_machine_type

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
    detail = f"x64 binary (emulated on ARM): {emulated[0]}"
    if pip_allowlisted(pip_name):
        detail += " [allowlist PASS]"
    return "emulated_amd64", detail


def audit_all_deps() -> list[dict[str, str]]:
    """Audit CRITICAL + OPTIONAL deps; return row dicts for reporting."""
    rows: list[dict[str, str]] = []
    for label, _import, pip_name in CRITICAL_PHASE0_DEPS + OPTIONAL_DEPS:
        arch, detail = audit_wheel_arch(pip_name)
        critical = pip_name.lower() in {p[2].lower() for p in CRITICAL_PHASE0_DEPS}
        perf_critical = pip_name.lower() in PERFORMANCE_CRITICAL_PACKAGES
        severity = wheel_severity(
            arch, pip_name, critical=critical, perf_critical=perf_critical
        )
        rows.append(
            {
                "package": label,
                "pip_name": pip_name,
                "arch": arch,
                "detail": detail,
                "severity": severity,
                "tier": "critical" if critical else "optional",
                "allowlisted": str(pip_allowlisted(pip_name)).lower(),
            }
        )
    return rows


__all__ = [
    "ALLOWLIST_EMULATION",
    "CRITICAL_PHASE0_DEPS",
    "OPTIONAL_DEPS",
    "PERFORMANCE_CRITICAL_PACKAGES",
    "audit_all_deps",
    "audit_wheel_arch",
]
