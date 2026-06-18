#!/usr/bin/env python3
"""UCGS v5 runner — config-driven architecture analysis with YAML output."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

from ucgs_checks import CheckResult, run_all_checks, severity_rank
from ucgs_checks.contract_drift import check_contract_drift
from ucgs_checks.forbidden_patterns import check_forbidden_patterns
from ucgs_checks.large_commit import check_large_commit
from ucgs_checks.layer_imports import check_layer_imports
from ucgs_config import find_project_root, load_config

CHECKS = {
    "layer_imports": check_layer_imports,
    "forbidden_patterns": check_forbidden_patterns,
    "large_commit": check_large_commit,
    "contract_drift": check_contract_drift,
}


def _git_available(project_root: Path) -> bool:
    return (project_root / ".git").exists()


def _collect_git_diff(project_root: Path) -> tuple[list[str], str, bool]:
    if not _git_available(project_root):
        return [], "", False

    try:
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        diff = subprocess.run(
            ["git", "diff", "--cached"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if staged.returncode != 0 or diff.returncode != 0:
            return [], "", False
        files = [line.strip() for line in staged.stdout.splitlines() if line.strip()]
        return files, diff.stdout, True
    except OSError:
        return [], "", False


def _read_phase_tag(config: dict[str, Any], project_root: Path) -> str:
    if config.get("phase"):
        return str(config["phase"])
    ledger = project_root / "docs" / "PHASE_LEDGER.md"
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
            if "Phase" in line and "—" in line:
                return line.strip("# ").strip()
    return "unknown"


def _compute_verdict(result: CheckResult) -> tuple[str, str]:
    if not result.violations and not result.warnings:
        return "PASS", "S1"

    max_violation = max((severity_rank(v.severity) for v in result.violations), default=0)
    max_warning = max((severity_rank(w.severity) for w in result.warnings), default=0)
    peak = max(max_violation, max_warning)

    severity_map = {0: "S1", 1: "S1", 2: "S2", 3: "S3", 4: "S4", 5: "S5"}
    risk = severity_map.get(peak, "S3")

    if max_violation >= 4:
        return "FAIL", risk
    if max_violation >= 3 or result.violations:
        return "WARN", risk
    if result.warnings:
        return "WARN", risk
    return "PASS", "S1"


def _debt_projection(verdict: str, violation_count: int) -> str:
    if verdict == "FAIL" or violation_count >= 3:
        return "accelerating"
    if verdict == "WARN" or violation_count >= 1:
        return "up"
    return "flat"


def _build_report(
    config: dict[str, Any],
    result: CheckResult,
    *,
    report_complete: bool,
    git_ok: bool,
    changed_files: list[str],
) -> dict[str, Any]:
    verdict, risk_level = _compute_verdict(result)
    contract_drift = bool(result.metadata.get("contract_drift", False))
    pipeline_bypass = any(
        v.rule_id in {"ui_no_services", "eventbus_bypass", "layer_import"}
        or v.classification == "CRITICAL"
        for v in result.violations
    )

    critical = sum(1 for v in result.violations if severity_rank(v.severity) >= 4)
    warnings = len(result.warnings) + sum(
        1 for v in result.violations if severity_rank(v.severity) < 4
    )

    if verdict == "FAIL":
        recommended = "block_merge"
    elif verdict == "WARN":
        recommended = "monitor"
    else:
        recommended = "none"

    return {
        "ucgs_summary": {
            "phase": config.get("ucgs_version", "v5"),
            "project_phase": _read_phase_tag(config, Path(config["_project_root"])),
            "profile": config.get("_profile", "default"),
            "verdict": verdict,
            "risk_level": risk_level,
            "architecture_trend": "degrading" if verdict == "FAIL" else "stable",
            "debt_trend": "increasing" if warnings else "stable",
            "contract_drift": contract_drift,
            "pipeline_bypass": pipeline_bypass,
            "critical_violations": critical,
            "warning_violations": warnings,
            "report_complete": report_complete,
            "git_available": git_ok,
            "prediction": {
                "next_phase_risk": "critical"
                if verdict == "FAIL"
                else ("medium" if verdict == "WARN" else "low"),
                "debt_projection": _debt_projection(verdict, len(result.violations)),
            },
            "recommended_action": recommended,
        },
        "violations": [
            {
                "rule_id": v.rule_id,
                "severity": v.severity,
                "classification": v.classification,
                "message": v.message,
                "file": v.file,
                "remediation": v.remediation,
            }
            for v in result.violations
        ],
        "warnings": [
            {
                "rule_id": w.rule_id,
                "severity": w.severity,
                "classification": w.classification,
                "message": w.message,
                "file": w.file,
                "remediation": w.remediation,
            }
            for w in result.warnings
        ],
        "context": {
            "changed_files": changed_files,
            "checks_run": list(CHECKS.keys()),
            "enforcement_mode": config.get("enforcement_mode", "warn"),
        },
    }


def run_ucgs(project_root: Path | None = None, write_local: bool = True) -> dict[str, Any]:
    root = project_root or find_project_root()
    config_path = root / "ucgs.config.yaml"
    report_complete = config_path.exists()

    if not report_complete:
        config: dict[str, Any] = {
            "_project_root": str(root),
            "_profile": "none",
            "enforcement_mode": "warn",
            "ucgs_version": "v5",
        }
        report = _build_report(
            config,
            CheckResult(),
            report_complete=False,
            git_ok=False,
            changed_files=[],
        )
        report["ucgs_summary"]["recommended_action"] = "run_llm_fallback"
        if write_local:
            (root / ".ucgs_last.yaml").write_text(
                yaml.dump(report, sort_keys=False), encoding="utf-8"
            )
        return report

    config = load_config(root)
    changed_files, diff_text, git_ok = _collect_git_diff(root)
    if not git_ok:
        report_complete = False

    result = run_all_checks(config, changed_files, diff_text, CHECKS)
    report = _build_report(
        config,
        result,
        report_complete=report_complete and git_ok,
        git_ok=git_ok,
        changed_files=changed_files,
    )

    if not report["ucgs_summary"]["report_complete"]:
        report["ucgs_summary"]["recommended_action"] = "run_llm_fallback"

    if write_local:
        (root / ".ucgs_last.yaml").write_text(
            yaml.dump(report, sort_keys=False), encoding="utf-8"
        )

    return report


def main() -> None:
    report = run_ucgs()
    print(yaml.dump(report, sort_keys=False))


if __name__ == "__main__":
    main()
