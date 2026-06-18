"""Pluggable UCGS architecture checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Violation:
    rule_id: str
    severity: str
    message: str
    file: str = ""
    classification: str = "RISKY"
    remediation: str = ""


@dataclass
class CheckResult:
    violations: list[Violation] = field(default_factory=list)
    warnings: list[Violation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


CheckFn = Callable[[dict[str, Any], list[str], list[str]], CheckResult]


def run_all_checks(
    config: dict[str, Any],
    changed_files: list[str],
    diff_text: str,
    checks: dict[str, CheckFn],
) -> CheckResult:
    aggregate = CheckResult()
    for name, check_fn in checks.items():
        result = check_fn(config, changed_files, diff_text.splitlines())
        aggregate.violations.extend(result.violations)
        aggregate.warnings.extend(result.warnings)
        aggregate.metadata[name] = result.metadata
    return aggregate


def severity_rank(severity: str) -> int:
    order = {"S0": 0, "S1": 1, "S2": 2, "S3": 3, "S4": 4, "S5": 5, "CRITICAL": 5}
    return order.get(severity.upper(), 2)
