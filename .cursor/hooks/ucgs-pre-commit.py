#!/usr/bin/env python3
"""Cursor hook: run UCGS before git commit and surface architecture verdict."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def allow(message: str = "") -> None:
    payload = {"permission": "allow"}
    if message:
        payload["agent_message"] = message
    print(json.dumps(payload))
    raise SystemExit(0)


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        allow()

    command = str(data.get("command", ""))
    if "git commit" not in command:
        allow()

    runner = ROOT / "tools" / "ucgs_runner.py"
    gate = ROOT / "tools" / "ucgs_ci_gate.py"
    if not runner.exists():
        allow("UCGS runner not installed in this project.")

    subprocess.run([PYTHON, str(runner)], cwd=ROOT, check=False)
    report_path = ROOT / ".ucgs_last.yaml"
    if not report_path.exists():
        allow(
            "UCGS report missing. Run full UCGS v4 LLM analysis per "
            ".cursor/rules/ucgs-v4-analysis.mdc before committing."
        )

    import yaml

    report = yaml.safe_load(report_path.read_text(encoding="utf-8")) or {}
    summary = report.get("ucgs_summary", {})
    verdict = summary.get("verdict", "WARN")
    complete = summary.get("report_complete", False)
    risk = summary.get("risk_level", "S2")

    messages = [f"UCGS verdict: {verdict} (risk {risk})"]
    if not complete:
        messages.append(
            "Report incomplete — perform UCGS v4 LLM analysis "
            "(see .cursor/rules/ucgs-v4-analysis.mdc)."
        )
    if verdict in {"WARN", "FAIL"}:
        messages.append(
            f"Violations: {summary.get('critical_violations', 0)} critical, "
            f"{summary.get('warning_violations', 0)} warnings."
        )

    allow(" | ".join(messages))


if __name__ == "__main__":
    main()
