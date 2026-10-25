#!/usr/bin/env python3
"""Capture ARM64 ISA evidence for platform-contract remediation (plan steps 2–3).

Does **not** grant allowlist exceptions. Does **not** change PE policy.
Does **not** claim this host is a release environment.

Operator: run with the same interpreter as ``main.py`` on Windows ARM64.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_command_center.platform.detector import (  # noqa: E402
    find_ollama_executable,
    get_architecture,
    get_pe_machine_type,
    is_arm64,
    ollama_available,
    validate_ollama_arm64_native,
)
from ai_command_center.platform.wheel_audit import audit_all_deps  # noqa: E402

_SCANNER_PATH = PROJECT_ROOT / "scripts" / "check_arm64_binaries.py"

# Plan §4.1 candidates — policy stays pending until operator evidence is reviewed.
ALLOWLIST_CANDIDATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("aiohttp_transitives", ("aiohttp", "yarl", "multidict", "frozenlist", "propcache")),
    ("watchdog", ("watchdog",)),
    ("pywin32", ("pywin32",)),
)

_NATIVE_SUFFIXES = {".pyd", ".dll", ".so", ".dylib"}


def _load_scanner():
    spec = importlib.util.spec_from_file_location("check_arm64_binaries", _SCANNER_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git_sha() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unavailable: {exc}"
    if proc.returncode != 0:
        return f"unavailable: {proc.stderr.strip() or proc.stdout.strip() or proc.returncode}"
    return proc.stdout.strip()


def _package_binaries(pip_name: str) -> dict[str, Any]:
    try:
        dist = importlib.metadata.distribution(pip_name)
    except importlib.metadata.PackageNotFoundError:
        return {
            "pip_name": pip_name,
            "installed": False,
            "files": [],
            "arch_summary": "not_installed",
        }

    files: list[dict[str, str]] = []
    kinds: list[str] = []
    for rel in dist.files or []:
        path = Path(str(dist.locate_file(rel)))
        if not path.is_file() or path.suffix.lower() not in _NATIVE_SUFFIXES:
            continue
        pe = get_pe_machine_type(path)
        kind = pe if pe != "UNKNOWN" else f"non_pe:{path.suffix.lower()}"
        kinds.append(kind)
        files.append({"path": str(path), "suffix": path.suffix.lower(), "pe": pe})

    if not files:
        arch = "pure_python_or_no_native_ext"
    elif all(k == "ARM64" for k in kinds):
        arch = "native_arm64_pe"
    elif all(k == "AMD64" for k in kinds):
        arch = "amd64_pe"
    else:
        arch = "mixed_or_non_pe"

    return {
        "pip_name": pip_name,
        "installed": True,
        "files": files,
        "arch_summary": arch,
    }


def collect_allowlist_candidates() -> list[dict[str, Any]]:
    """Build §4.1 rows. policy is always pending — never allow/deny here."""
    rows: list[dict[str, Any]] = []
    for row_id, packages in ALLOWLIST_CANDIDATES:
        pkg_details = [_package_binaries(name) for name in packages]
        summaries = {p["arch_summary"] for p in pkg_details}
        if summaries == {"not_installed"}:
            why = "n/a_not_installed"
        elif summaries <= {"native_arm64_pe", "pure_python_or_no_native_ext", "not_installed"}:
            why = "n/a_no_amd64_pe_observed"
        elif "amd64_pe" in summaries or "mixed_or_non_pe" in summaries:
            why = "unestablished"
        else:
            why = "unestablished"
        rows.append(
            {
                "row_id": row_id,
                "packages": pkg_details,
                "inference_critical": False,
                "why_emulation_exists": why,
                "runtime_impact": "unestablished",
                "policy": "pending",
            }
        )
    return rows


def collect_payload(*, include_scanner: bool = True) -> dict[str, Any]:
    scanner_report: dict[str, Any]
    if include_scanner:
        scanner = _load_scanner()
        if sys.platform != "win32":
            scanner_report = {
                "skipped": True,
                "reason": "non-Windows host: no PE binaries to validate",
            }
        else:
            scanner_report = scanner.scan(scanner.default_scan_roots(), allow=set())
    else:
        scanner_report = {"skipped": True, "reason": "include_scanner=false"}

    ollama_path = find_ollama_executable()
    oll_http_ok, oll_http_detail = ollama_available()
    oll_pe_ok, oll_pe_detail = validate_ollama_arm64_native()
    python_pe = get_pe_machine_type(sys.executable)

    return {
        "schema": "acc.arm64_isa_evidence.v1",
        "policy_note": (
            "Allowlist candidates are pending. compatibility_matrix WARN is not a grant. "
            "This file is evidence, not a policy decision."
        ),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "host": {
            "sys_platform": sys.platform,
            "processor_architecture": os.environ.get("PROCESSOR_ARCHITECTURE"),
            "processor_architew6432": os.environ.get("PROCESSOR_ARCHITEW6432"),
            "platform_machine": get_architecture(),
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
            "platform_machine": get_architecture(),
            "is_arm64_fn": is_arm64(),
            "pe_machine": python_pe,
        },
        "ollama": {
            "exe": str(ollama_path) if ollama_path else None,
            "http_ok": oll_http_ok,
            "http_detail": oll_http_detail,
            "pe_ok": oll_pe_ok,
            "pe_detail": oll_pe_detail,
        },
        "release_environment_claim": (
            "valid_only_on_windows_arm64_native_python"
            if sys.platform == "win32" and is_arm64() and python_pe == "ARM64"
            else "not_a_native_arm64_release_environment"
        ),
        "scanner": scanner_report,
        "wheel_audit": audit_all_deps(),
        "allowlist_candidates": collect_allowlist_candidates(),
    }


def run_preflight() -> dict[str, Any]:
    script = PROJECT_ROOT / "scripts" / "preflight_arm64.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ran": False, "error": str(exc)}
    return {
        "ran": True,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="write JSON payload to this path")
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="do not subprocess scripts/preflight_arm64.py",
    )
    parser.add_argument(
        "--skip-scanner",
        action="store_true",
        help="skip env PE scan (tests)",
    )
    args = parser.parse_args(argv)

    payload = collect_payload(include_scanner=not args.skip_scanner)
    if not args.skip_preflight:
        payload["preflight"] = run_preflight()
    else:
        payload["preflight"] = {"ran": False, "reason": "skipped"}

    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)

    print(
        "ISA capture complete. policy=pending for allowlist candidates. "
        f"release_environment_claim={payload['release_environment_claim']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
