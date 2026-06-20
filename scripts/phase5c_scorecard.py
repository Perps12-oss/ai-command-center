#!/usr/bin/env python3
"""Phase 5C scorecard — record and validate daily-driver stress test results."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = PROJECT_ROOT / "docs" / "templates" / "phase5c_scorecard.json"

_SCORE_KEYS = (
    "core_loop",
    "context_handling",
    "ui_experience",
    "failure_recovery",
    "overall_trust",
)

_PASS_THRESHOLDS = {
    "core_loop": 4,
    "context_handling": 4,
    "failure_recovery": 4,
}


def _scorecard_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise OSError("APPDATA not set")
    root = Path(appdata) / "AICommandCenter"
    root.mkdir(parents=True, exist_ok=True)
    return root / "phase5c_scorecard.json"


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _load() -> dict:
    path = _scorecard_path()
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def _save(data: dict) -> Path:
    path = _scorecard_path()
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _prompt_score(label: str) -> int:
    while True:
        raw = input(f"{label} (1-5): ").strip()
        try:
            value = int(raw)
        except ValueError:
            print("  Enter an integer 1–5.")
            continue
        if 1 <= value <= 5:
            return value
        print("  Score must be 1–5.")


def cmd_record() -> int:
    data = _load()
    print("=== Phase 5C Scorecard ===\n")
    print("Score each category 1–5 (see docs/PHASE5C_STRESS_TEST.md).\n")

    data["date"] = date.today().isoformat()
    data["tester"] = input("Tester name: ").strip() or data.get("tester", "")
    data["git_sha"] = _git_sha()
    freeze = input("Freeze confirmed (no code changes during test)? [Y/n]: ").strip().lower()
    data["freeze_confirmed"] = freeze not in ("n", "no")
    preflight = input("Preflight PASS? [Y/n]: ").strip().lower()
    data["preflight_pass"] = preflight not in ("n", "no")

    scores = data.setdefault("scores", {})
    for key in _SCORE_KEYS:
        label = key.replace("_", " ").title()
        scores[key] = _prompt_score(label)

    natural = input("Natural reuse without thinking? [y/N]: ").strip().lower()
    data["natural_reuse"] = natural in ("y", "yes")

    notes = data.setdefault("layer_notes", {})
    print("\nOptional layer notes (Enter to skip):")
    for layer in (
        "layer1_core_loop",
        "layer2_context_stress",
        "layer3_ui_usability",
        "layer4_failure_modes",
    ):
        line = input(f"  {layer}: ").strip()
        if line:
            notes[layer] = line

    blockers_raw = input("Blockers (comma-separated, or Enter): ").strip()
    data["blockers"] = [b.strip() for b in blockers_raw.split(",") if b.strip()]

    path = _save(data)
    print(f"\nSaved: {path}")
    return cmd_validate()


def cmd_show() -> int:
    path = _scorecard_path()
    if not path.is_file():
        print(f"No scorecard at {path}")
        print(f"Run: {PY} scripts/phase5c_scorecard.py record")
        return 1
    print(path.read_text(encoding="utf-8"))
    return 0


def validate_scorecard(data: dict) -> list[str]:
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


def cmd_validate() -> int:
    path = _scorecard_path()
    if not path.is_file():
        print(f"FAIL: no scorecard at {path}")
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    failures = validate_scorecard(data)
    if failures:
        print("SCORECARD: FAIL")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("SCORECARD: PASS (gold standard met)")
    scores = data.get("scores", {})
    print(
        f"  core={scores.get('core_loop')} context={scores.get('context_handling')} "
        f"failure={scores.get('failure_recovery')} trust={scores.get('overall_trust')}"
    )
    return 0


PY = sys.executable


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: phase5c_scorecard.py {record|show|validate}")
        return 2
    cmd = sys.argv[1].lower()
    if cmd == "record":
        return cmd_record()
    if cmd == "show":
        return cmd_show()
    if cmd == "validate":
        return cmd_validate()
    print(f"Unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
