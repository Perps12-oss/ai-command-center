#!/usr/bin/env python3
"""Comprehensive ARM64 preflight checks for AI Command Center (Phase 0)."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_command_center.platform.detector import (  # noqa: E402
    get_architecture,
    get_ram_mb,
    is_arm64,
    ollama_available,
)

CORE_DEPS: list[tuple[str, str, str]] = [
    ("customtkinter", "customtkinter", "customtkinter"),
    ("CTkMessagebox", "CTkMessagebox", "CTkMessagebox"),
    ("aiohttp", "aiohttp", "aiohttp"),
    ("mistune", "mistune", "mistune"),
    ("psutil", "psutil", "psutil"),
    ("pystray", "pystray", "pystray"),
    ("Pillow", "PIL", "Pillow"),
    ("keyboard", "keyboard", "keyboard"),
    ("watchdog", "watchdog", "watchdog"),
    ("pywin32", "win32api", "pywin32"),
    ("pyyaml", "yaml", "pyyaml"),
]


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def check_python_version() -> tuple[bool, str]:
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (3, 11)
    detail = f"{major}.{minor}.{sys.version_info.micro} ({sys.executable})"
    return ok, detail


def check_arm64() -> tuple[bool, str]:
    arch = get_architecture()
    ok = is_arm64()
    return ok, arch


def check_ram() -> tuple[bool, str]:
    try:
        ram = get_ram_mb()
    except Exception as exc:  # noqa: BLE001
        return False, f"unable to read RAM: {exc}"
    detail = (
        f"total {ram['total_gb']} GB ({ram['total_mb']} MB), "
        f"available {ram['available_gb']} GB ({ram['available_mb']} MB)"
    )
    return True, detail


def check_ollama_http() -> tuple[bool, str]:
    ok, detail = ollama_available()
    return ok, detail


def _ollama_process_arch_hint() -> tuple[bool, str]:
    try:
        import psutil
    except ImportError:
        return False, "psutil not installed (cannot inspect Ollama process)"

    procs = []
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if "ollama" in name:
                procs.append(proc)
        except (psutil.Error, OSError):
            continue

    if not procs:
        return False, "no Ollama process found (service may be stopped)"

    hints: list[str] = []
    for proc in procs:
        exe = proc.info.get("exe") or ""
        exe_lower = exe.lower()
        hint = "arch unknown"
        if exe_lower:
            if "arm64" in exe_lower or "aarch64" in exe_lower:
                hint = "likely native ARM64 (path hint)"
            elif "program files (x86)" in exe_lower or "x64" in exe_lower:
                hint = "likely x64/emulated (path hint)"
            elif "windowsapps" in exe_lower:
                hint = "store/emulated path hint"
            else:
                hint = f"path: {exe}"
        try:
            import platform

            if hasattr(platform, "win32_is_native_arm64"):
                # Best-effort: compare with system ARM64
                if is_arm64() and "program files\\ollama" in exe_lower.replace("/", "\\"):
                    hint = "typical native install path"
        except Exception:
            pass
        hints.append(f"{proc.info.get('name')} -> {hint}")

    return True, "; ".join(hints)


def _dep_available(pip_name: str, import_name: str) -> tuple[bool, str]:
    if importlib.util.find_spec(import_name) is not None:
        return True, "import ok"
    if shutil.which("pip"):
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "show", pip_name],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if proc.returncode == 0:
                return True, "pip show ok (import failed)"
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"pip show error: {exc}"
    return False, "missing"


def check_dependencies() -> tuple[bool, list[tuple[str, bool, str]]]:
    rows: list[tuple[str, bool, str]] = []
    all_ok = True
    for label, import_name, pip_name in CORE_DEPS:
        ok, detail = _dep_available(pip_name, import_name)
        rows.append((label, ok, detail))
        if not ok:
            all_ok = False
    return all_ok, rows


def main() -> int:
    print("=== AI Command Center — ARM64 Preflight (Phase 0) ===")
    print(f"Project root: {PROJECT_ROOT}")
    print()

    critical_fail = False
    warnings = 0

    py_ok, py_detail = check_python_version()
    print(f"[{_status(py_ok)}] Python >= 3.11: {py_detail}")
    if not py_ok:
        critical_fail = True

    arm_ok, arm_detail = check_arm64()
    print(f"[{_status(arm_ok)}] platform.machine() ARM64: {arm_detail}")
    if not arm_ok:
        critical_fail = True
        print("       WARNING: Use native ARM64 Python (not x64-emulated AMD64).")

    ram_ok, ram_detail = check_ram()
    print(f"[{_status(ram_ok)}] System RAM: {ram_detail}")

    oll_ok, oll_detail = check_ollama_http()
    print(f"[{_status(oll_ok)}] Ollama HTTP /api/tags: {oll_detail}")
    if not oll_ok:
        critical_fail = True

    proc_ok, proc_detail = _ollama_process_arch_hint()
    print(f"[{_status(proc_ok)}] Ollama process arch hint: {proc_detail}")
    if not proc_ok:
        warnings += 1

    deps_ok, dep_rows = check_dependencies()
    print(f"[{_status(deps_ok)}] Core dependency availability:")
    for label, ok, detail in dep_rows:
        print(f"       [{_status(ok)}] {label}: {detail}")
    if not deps_ok:
        warnings += 1

    print()
    if critical_fail:
        print("RESULT: CRITICAL CHECKS FAILED (ARM64 and/or Ollama and/or Python version).")
        return 1
    if warnings:
        print("RESULT: Critical checks passed with warnings (deps/process hints).")
        return 0
    print("RESULT: All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
