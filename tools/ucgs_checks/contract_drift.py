"""Detect unversioned changes to locked contract files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import CheckResult, Violation


def check_contract_drift(
    config: dict[str, Any],
    changed_files: list[str],
    diff_lines: list[str],
) -> CheckResult:
    result = CheckResult()
    contracts = config.get("rules", {}).get("contract_lock", {})
    if not contracts:
        return result

    contract_files = contracts.get("files", [])
    required_fields = contracts.get("required_fields", [])
    project_root = Path(config.get("_project_root", "."))

    normalized_changed = {path.replace("\\", "/") for path in changed_files}
    touched = [path for path in contract_files if path.replace("\\", "/") in normalized_changed]

    if not touched:
        result.metadata["contract_drift"] = False
        return result

    drift_detected = False
    for rel_path in touched:
        full_path = project_root / rel_path
        if not full_path.exists():
            drift_detected = True
            result.violations.append(
                Violation(
                    rule_id="contract_missing",
                    severity="S4",
                    message=f"Contract file missing: {rel_path}",
                    file=rel_path,
                    classification="CRITICAL",
                    remediation="Restore contract file or bump version with migration plan.",
                )
            )
            continue

        text = full_path.read_text(encoding="utf-8", errors="replace")
        for field in required_fields:
            if not re.search(re.escape(field), text):
                drift_detected = True
                result.violations.append(
                    Violation(
                        rule_id="contract_field_missing",
                        severity="S4",
                        message=f"Required contract field '{field}' missing in {rel_path}",
                        file=rel_path,
                        classification="CRITICAL",
                        remediation="Add version field or restore locked contract schema.",
                    )
                )

        added_lines = [
            line[1:]
            for line in diff_lines
            if line.startswith("+") and not line.startswith("+++")
        ]
        if any("version" not in line.lower() for line in added_lines):
            for line in added_lines:
                if re.search(r"(class|def|schema|contract)", line, re.IGNORECASE):
                    drift_detected = True
                    result.warnings.append(
                        Violation(
                            rule_id="contract_unversioned_change",
                            severity="S3",
                            message=f"Contract file changed without explicit version bump: {rel_path}",
                            file=rel_path,
                            classification="DANGEROUS",
                            remediation="Bump contract version and update SUPPORTED_VERSIONS.",
                        )
                    )
                    break

    result.metadata["contract_drift"] = drift_detected
    result.metadata["touched_contracts"] = touched
    return result
