#!/usr/bin/env python3
"""UCGS v5 runner — config-driven architecture analysis with YAML output."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

from ucgs_checks import CheckResult, Violation, run_all_checks, severity_rank
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

# Diff modes:
#   staged — local pre-commit (git diff --cached)
#   range  — CI PR/push (git diff <base>...HEAD); requires UCGS_DIFF_BASE
DIFF_MODE_STAGED = "staged"
DIFF_MODE_RANGE = "range"


def _git_available(project_root: Path) -> bool:
    return (project_root / ".git").exists()


def resolve_diff_mode() -> str:
    """Return ``staged`` or ``range``.

    Local pre-commit defaults to staged. CI must set ``UCGS_DIFF_MODE=range``
    (and ``UCGS_DIFF_BASE``) so a clean checkout is not audited as an empty
    staged index.
    """
    raw = os.getenv("UCGS_DIFF_MODE", DIFF_MODE_STAGED).strip().lower()
    if raw in {"ci", "pr", "range"}:
        return DIFF_MODE_RANGE
    if raw in {"", "staged", "cached", "local"}:
        return DIFF_MODE_STAGED
    return DIFF_MODE_STAGED


def _run_git(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _collect_staged_diff(project_root: Path) -> tuple[list[str], str, bool]:
    staged = _run_git(project_root, "diff", "--cached", "--name-only")
    diff = _run_git(project_root, "diff", "--cached")
    if staged.returncode != 0 or diff.returncode != 0:
        return [], "", False
    files = [line.strip() for line in staged.stdout.splitlines() if line.strip()]
    return files, diff.stdout, True


def _collect_range_diff(
    project_root: Path,
    *,
    base: str,
    head: str,
) -> tuple[list[str], str, bool]:
    """Three-dot diff ``base...head`` — commits reachable from head not from base."""
    if not base.strip():
        return [], "", False
    head_ref = head.strip() or "HEAD"
    # Ensure base is resolvable (shallow clones must fetch with adequate depth).
    resolve = _run_git(project_root, "rev-parse", "--verify", base)
    if resolve.returncode != 0:
        return [], "", False
    names = _run_git(project_root, "diff", "--name-only", f"{base}...{head_ref}")
    patch = _run_git(project_root, "diff", f"{base}...{head_ref}")
    if names.returncode != 0 or patch.returncode != 0:
        return [], "", False
    files = [line.strip() for line in names.stdout.splitlines() if line.strip()]
    return files, patch.stdout, True


def _collect_git_diff(project_root: Path) -> tuple[list[str], str, bool, str]:
    """Return ``(changed_files, diff_text, git_ok, diff_mode)``."""
    if not _git_available(project_root):
        return [], "", False, resolve_diff_mode()

    mode = resolve_diff_mode()
    try:
        if mode == DIFF_MODE_RANGE:
            base = os.getenv("UCGS_DIFF_BASE", "").strip()
            head = os.getenv("UCGS_DIFF_HEAD", "HEAD").strip() or "HEAD"
            files, diff_text, ok = _collect_range_diff(
                project_root, base=base, head=head
            )
            return files, diff_text, ok, mode
        files, diff_text, ok = _collect_staged_diff(project_root)
        return files, diff_text, ok, mode
    except OSError:
        return [], "", False, mode


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
    diff_mode: str = DIFF_MODE_STAGED,
    diff_base: str = "",
    diff_head: str = "",
) -> dict[str, Any]:
    verdict, risk_level = _compute_verdict(result)
    cd_meta = result.metadata.get("contract_drift", False)
    if isinstance(cd_meta, dict):
        contract_drift = bool(cd_meta.get("contract_drift", False))
    else:
        contract_drift = bool(cd_meta)
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
            "diff_mode": diff_mode,
            "diff_base": diff_base,
            "diff_head": diff_head,
        },
    }


def run_ucgs(project_root: Path | None = None, write_local: bool = True) -> dict[str, Any]:
    root = project_root or find_project_root()
    config_path = root / "ucgs.config.yaml"
    report_complete = config_path.exists()
    diff_mode = resolve_diff_mode()
    diff_base = os.getenv("UCGS_DIFF_BASE", "").strip()
    diff_head = os.getenv("UCGS_DIFF_HEAD", "HEAD").strip() or "HEAD"

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
            diff_mode=diff_mode,
            diff_base=diff_base,
            diff_head=diff_head,
        )
        report["ucgs_summary"]["recommended_action"] = "run_llm_fallback"
        if write_local:
            (root / ".ucgs_last.yaml").write_text(
                yaml.dump(report, sort_keys=False), encoding="utf-8"
            )
        return report

    config = load_config(root)
    changed_files, diff_text, git_ok, diff_mode = _collect_git_diff(root)
    if not git_ok:
        report_complete = False
        # Range mode without a resolvable base must not silently PASS as empty.
        if diff_mode == DIFF_MODE_RANGE:
            report = _build_report(
                config,
                CheckResult(
                    violations=[
                        Violation(
                            rule_id="ucgs_diff_range_unresolved",
                            severity="S4",
                            message=(
                                "UCGS_DIFF_MODE=range but base/head diff could not be "
                                "resolved (set UCGS_DIFF_BASE to the PR/push merge-base)."
                            ),
                            classification="CRITICAL",
                            remediation=(
                                "Checkout with fetch-depth: 0 and export UCGS_DIFF_BASE / "
                                "UCGS_DIFF_HEAD from the CI event."
                            ),
                        )
                    ]
                ),
                report_complete=False,
                git_ok=False,
                changed_files=[],
                diff_mode=diff_mode,
                diff_base=diff_base,
                diff_head=diff_head,
            )
            if write_local:
                (root / ".ucgs_last.yaml").write_text(
                    yaml.dump(report, sort_keys=False), encoding="utf-8"
                )
            return report

    result = run_all_checks(config, changed_files, diff_text, CHECKS)
    report = _build_report(
        config,
        result,
        report_complete=report_complete and git_ok,
        git_ok=git_ok,
        changed_files=changed_files,
        diff_mode=diff_mode,
        diff_base=diff_base if diff_mode == DIFF_MODE_RANGE else "",
        diff_head=diff_head if diff_mode == DIFF_MODE_RANGE else "",
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
