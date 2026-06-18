#!/usr/bin/env python3
"""UCGS v5 CI gate — evaluates runner YAML and enforces verdict."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ucgs_config import find_project_root, get_enforcement_mode, load_config

FAIL_STATES = {"FAIL"}
BLOCKING_RISKS = {"S4", "S5"}


def main(path: str) -> int:
    report_path = Path(path)
    if not report_path.exists():
        print("[UCGS BLOCK] report file missing")
        return 1 if get_enforcement_mode(load_config(find_project_root())) == "block" else 0

    with report_path.open("r", encoding="utf-8") as handle:
        report = yaml.safe_load(handle) or {}

    summary = report.get("ucgs_summary", {})
    verdict = str(summary.get("verdict", "WARN")).upper()
    risk = str(summary.get("risk_level", "S2")).upper()
    enforcement = get_enforcement_mode(load_config(find_project_root()))

    should_block = verdict in FAIL_STATES or risk in BLOCKING_RISKS

    if should_block:
        print("[UCGS BLOCK] Architecture violation detected")
        print(f"   verdict={verdict} risk_level={risk} enforcement={enforcement}")
        if enforcement == "block":
            return 1
        print("[UCGS WARN] warn mode: commit/merge not blocked (Phase 1)")
        return 0

    if verdict == "WARN":
        print("[UCGS WARNING] Review recommended")
        print(f"   risk_level={risk}")
        print("[UCGS PASS] with warnings")
        return 0

    print("[UCGS PASS]")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/ucgs_ci_gate.py <report.yaml>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
