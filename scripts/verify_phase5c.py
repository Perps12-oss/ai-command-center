#!/usr/bin/env python3
"""Phase 5C gate — preflight PASS + scorecard gold standard."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_PASS_THRESHOLDS = {
    "core_loop": 4,
    "context_handling": 4,
    "failure_recovery": 4,
}
_SCORE_KEYS = (
    "core_loop",
    "context_handling",
    "ui_experience",
    "failure_recovery",
    "overall_trust",
)


def _scorecard_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise OSError("APPDATA not set")
    return Path(appdata) / "AICommandCenter" / "phase5c_scorecard.json"


def _validate_scorecard(data: dict) -> list[str]:
    failures: list[str] = []
    if not data.get("freeze_confirmed"):
        failures.append("freeze_confirmed must be true")
    if not data.get("preflight_pass"):
        failures.append("preflight_pass must be true (run verify_phase5c_preflight.py)")
    if not data.get("natural_reuse"):
        failures.append("natural_reuse must be true for gold standard")

    scores = data.get("scores") or {}
    for key, minimum in _PASS_THRESHOLDS.items():
        value = scores.get(key)
        if not isinstance(value, int) or value < minimum:
            failures.append(f"scores.{key} must be >={minimum} (got {value!r})")

    for key in _SCORE_KEYS:
        value = scores.get(key)
        if not isinstance(value, int) or not 1 <= value <= 5:
            failures.append(f"scores.{key} must be 1–5 (got {value!r})")

    blockers = data.get("blockers") or []
    if blockers:
        failures.append(f"blockers present: {blockers}")

    return failures


def main() -> int:
    print("=== Phase 5C Gate Verification ===")
    failures: list[str] = []

    preflight = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "verify_phase5c_preflight.py")],
        cwd=PROJECT_ROOT,
    )
    if preflight.returncode != 0:
        failures.append("preflight failed (verify_phase5c_preflight.py)")

    path = _scorecard_path()
    if not path.is_file():
        failures.append(
            f"scorecard missing: {path} — run scripts/phase5c_scorecard.py record"
        )
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        failures.extend(_validate_scorecard(data))

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        print("\nGate history: docs/ARCHITECTURE.md#gate-history")
        return 1

    print("PASS: Phase 5C — daily driver stress test gold standard met")
    print(f"  scorecard: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
