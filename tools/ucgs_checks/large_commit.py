"""Warn when commits are too large for safe architectural review."""

from __future__ import annotations

from typing import Any

from . import CheckResult, Violation


def check_large_commit(
    config: dict[str, Any],
    changed_files: list[str],
    diff_lines: list[str],
) -> CheckResult:
    result = CheckResult()
    rule = config.get("rules", {}).get("large_commit", {})
    if not rule:
        return result

    max_files = int(rule.get("max_files", 25))
    max_added_lines = int(rule.get("max_added_lines", 500))

    added_lines = [line for line in diff_lines if line.startswith("+") and not line.startswith("+++")]

    if len(changed_files) > max_files:
        result.warnings.append(
            Violation(
                rule_id="large_commit_files",
                severity=rule.get("severity", "S2"),
                message=(
                    f"Commit touches {len(changed_files)} files "
                    f"(limit {max_files}); consider splitting."
                ),
                classification="STRUCTURAL",
                remediation="Split into smaller commits aligned to architectural boundaries.",
            )
        )

    if len(added_lines) > max_added_lines:
        result.warnings.append(
            Violation(
                rule_id="large_commit_lines",
                severity=rule.get("severity", "S2"),
                message=(
                    f"Commit adds {len(added_lines)} lines "
                    f"(limit {max_added_lines}); review risk is elevated."
                ),
                classification="RISKY",
                remediation="Decompose changes by subsystem before merge.",
            )
        )

    result.metadata["changed_files"] = len(changed_files)
    result.metadata["added_lines"] = len(added_lines)
    return result
