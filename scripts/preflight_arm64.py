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
    get_baseline_log_path,
    get_ram_mb,
    is_arm64,
    ollama_available,
    read_baseline_log,
    validate_ollama_arm64_native,
)
from ai_command_center.platform.wheel_audit import (  # noqa: E402
    CRITICAL_PHASE0_DEPS,
    OPTIONAL_DEPS,
    audit_all_deps,
)


def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _severity_label(severity: str) -> str:
    return severity


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


def check_baseline_logged() -> tuple[bool, str]:
    path = get_baseline_log_path()
    data = read_baseline_log()
    if data is None:
        return False, f"missing — run: python scripts/benchmark_startup.py (expected {path})"
    ts = data.get("timestamp", "unknown")
    startup = data.get("startup", {})
    import_ms = startup.get("package_import_ms", "?")
    ram = data.get("ram", {})
    avail = ram.get("available_gb", "?")
    return True, f"found {path.name} @ {ts} (import {import_ms} ms, avail {avail} GB)"


def check_ollama_http() -> tuple[bool, str]:
    ok, detail = ollama_available()
    return ok, detail


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


def check_critical_dependencies() -> tuple[bool, list[tuple[str, bool, str]]]:
    rows: list[tuple[str, bool, str]] = []
    all_ok = True
    for label, import_name, pip_name in CRITICAL_PHASE0_DEPS:
        ok, detail = _dep_available(pip_name, import_name)
        rows.append((label, ok, detail))
        if not ok:
            all_ok = False
    return all_ok, rows


def check_optional_dependencies() -> tuple[bool, list[tuple[str, bool, str]]]:
    rows: list[tuple[str, bool, str]] = []
    all_ok = True
    for label, import_name, pip_name in OPTIONAL_DEPS:
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
        print("       Use native ARM64 Python (not x64-emulated AMD64).")

    ram_ok, ram_detail = check_ram()
    print(f"[{_status(ram_ok)}] System RAM: {ram_detail}")

    baseline_ok, baseline_detail = check_baseline_logged()
    print(f"[{_status(baseline_ok)}] Baseline RAM logged (baseline.json): {baseline_detail}")
    if not baseline_ok:
        critical_fail = True

    oll_ok, oll_detail = check_ollama_http()
    print(f"[{_status(oll_ok)}] Ollama HTTP /api/tags: {oll_detail}")
    if not oll_ok:
        critical_fail = True

    oll_arch_ok, oll_arch_detail = validate_ollama_arm64_native()
    print(f"[{_status(oll_arch_ok)}] Ollama native ARM64 PE: {oll_arch_detail}")
    if not oll_arch_ok:
        critical_fail = True

    crit_ok, crit_rows = check_critical_dependencies()
    print(f"[{_status(crit_ok)}] Critical Phase 0 dependencies:")
    for label, ok, detail in crit_rows:
        print(f"       [{_status(ok)}] {label}: {detail}")
    if not crit_ok:
        critical_fail = True

    opt_ok, opt_rows = check_optional_dependencies()
    print(f"[{_status(opt_ok)}] Optional stack dependencies (requirements.txt):")
    for label, ok, detail in opt_rows:
        print(f"       [{_status(ok)}] {label}: {detail}")
    if not opt_ok:
        warnings += 1

    wheel_rows = audit_all_deps()
    print("[INFO] Wheel architecture audit (emulated x64 = WARN unless inference-critical):")
    for row in wheel_rows:
        sev = row["severity"]
        print(
            f"       [{_severity_label(sev)}] {row['package']}: "
            f"{row['arch']} — {row['detail']}"
        )
        if sev == "FAIL":
            critical_fail = True
        elif sev == "WARN":
            warnings += 1

    print()
    if critical_fail:
        print("RESULT: CRITICAL CHECKS FAILED — Phase 0 gate not passed.")
        return 1
    if warnings:
        print("RESULT: Phase 0 passed with warnings (see compatibility_matrix.md).")
        return 0
    print("RESULT: Phase 0 gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
