#!/usr/bin/env python3
"""Phase 5C preflight — automated gates before manual stress test."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

_SCRIPTS = (
    "verify_contracts.py",
    "verify_phase3d.py",
    "verify_phase4a.py",
    "verify_phase4b.py",
    "verify_phase4c.py",
    "verify_phase4d_compression.py",
    "verify_phase4e.py",
    "verify_phase4f.py",
    "verify_phase5a.py",
    "verify_phase5b.py",
    "audit_note_integration.py",
)

# Live Ollama integration tests are optional in CI; they require `ollama serve`.
_OPTIONAL_SCRIPTS = ("run_daily_driver.py",)


def _run(script: str) -> tuple[bool, str]:
    path = PROJECT_ROOT / "scripts" / script
    result = subprocess.run(
        [PY, str(path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    ok = result.returncode == 0
    tail = (result.stdout + result.stderr).strip().splitlines()
    summary = tail[-1] if tail else f"exit {result.returncode}"
    return ok, summary


def main() -> int:
    print("=== Phase 5C Preflight (freeze before manual stress test) ===\n")
    failures: list[str] = []
    warnings: list[str] = []

    for script in _SCRIPTS:
        print(f"--- {script} ---")
        ok, summary = _run(script)
        print(f"  {'PASS' if ok else 'FAIL'}: {summary}")
        if not ok:
            failures.append(script)

    for script in _OPTIONAL_SCRIPTS:
        print(f"--- {script} (optional) ---")
        ok, summary = _run(script)
        print(f"  {'PASS' if ok else 'WARN'}: {summary}")
        if not ok:
            warnings.append(script)

    if warnings:
        print("\nPREFLIGHT WARNINGS — optional gates failed (may require live Ollama):")
        for item in warnings:
            print(f"  - {item}")

    if failures:
        print("\nPREFLIGHT FAIL — fix before Layer 1–4 manual testing:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("\nPREFLIGHT PASS — safe to run manual stress test (docs/PHASE5C_STRESS_TEST.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
