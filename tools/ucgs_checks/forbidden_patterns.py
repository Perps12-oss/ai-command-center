"""Detect scope creep and forbidden patterns in diffs."""

from __future__ import annotations

import re
from typing import Any

from . import CheckResult, Violation


def check_forbidden_patterns(
    config: dict[str, Any],
    changed_files: list[str],
    diff_lines: list[str],
) -> CheckResult:
    result = CheckResult()
    patterns = config.get("rules", {}).get("forbidden_patterns", [])
    if not patterns:
        return result

    added_lines = [line[1:] for line in diff_lines if line.startswith("+") and not line.startswith("+++")]

    for rule in patterns:
        pattern = rule.get("pattern", "")
        if not pattern:
            continue
        regex = re.compile(pattern, re.IGNORECASE)
        for line in added_lines:
            if regex.search(line):
                severity = rule.get("severity", "S4")
                bucket = result.violations if severity in {"S3", "S4", "S5", "CRITICAL"} else result.warnings
                bucket.append(
                    Violation(
                        rule_id=rule.get("id", "forbidden_pattern"),
                        severity=severity,
                        message=rule.get("message", f"Forbidden pattern matched: {pattern}"),
                        classification=rule.get("classification", "CRITICAL"),
                        remediation=rule.get(
                            "remediation",
                            "Remove scope creep or enable the feature in a dedicated phase.",
                        ),
                    )
                )

    result.metadata["patterns_evaluated"] = len(patterns)
    return result
