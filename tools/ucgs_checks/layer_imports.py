"""Detect forbidden imports across architectural layers."""

from __future__ import annotations

import fnmatch
import re
from pathlib import PurePosixPath
from typing import Any

from . import CheckResult, Violation


def _matches_any(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    posix = PurePosixPath(normalized)
    for pattern in patterns:
        if hasattr(posix, "full_match"):
            try:
                if posix.full_match(pattern):
                    return True
            except re.error:
                pass
        if posix.match(pattern):
            return True
        if fnmatch.fnmatch(normalized, pattern):
            return True
    return False


def _extract_imports(line: str) -> list[str]:
    imports: list[str] = []
    stripped = line.strip()

    from_match = re.match(r"^from\s+([\w\.]+)\s+import\s+(.+)$", stripped)
    if from_match:
        imports.append(from_match.group(1))
        symbols = from_match.group(2).split(",")
        for symbol in symbols:
            token = symbol.strip().split(" as ")[0].strip()
            if token and token != "*":
                imports.append(token)
        return imports

    import_match = re.match(r"^import\s+(.+)$", stripped)
    if import_match:
        for part in import_match.group(1).split(","):
            token = part.strip().split(" as ")[0].strip()
            if token:
                imports.append(token)
    return imports


def _matches_forbidden(name: str, pattern: str) -> bool:
    if fnmatch.fnmatch(name, pattern):
        return True
    if pattern.strip("*") and pattern.strip("*").lower() in name.lower():
        return True
    leaf = name.split(".")[-1]
    return fnmatch.fnmatch(leaf, pattern)


def check_layer_imports(
    config: dict[str, Any],
    changed_files: list[str],
    diff_lines: list[str],
) -> CheckResult:
    result = CheckResult()
    rules = config.get("rules", {}).get("layer_boundaries", [])
    if not rules:
        return result

    current_file = ""
    for line in diff_lines:
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if not current_file:
            continue

        content = line[1:]
        for rule in rules:
            paths = rule.get("paths", [])
            forbidden = rule.get("forbidden_imports", [])
            if not paths or not forbidden:
                continue
            if not _matches_any(current_file, paths):
                continue

            for imported in _extract_imports(content):
                for pattern in forbidden:
                    if _matches_forbidden(imported, pattern):
                        severity = rule.get("severity", "S3")
                        result.violations.append(
                            Violation(
                                rule_id=rule.get("id", "layer_import"),
                                severity=severity,
                                message=(
                                    f"Forbidden import '{imported}' in layer path "
                                    f"'{current_file}' (rule: {rule.get('name', 'layer_boundary')})"
                                ),
                                file=current_file,
                                classification=rule.get("classification", "DANGEROUS"),
                                remediation=rule.get(
                                    "remediation",
                                    "Route access through canonical pipeline layers.",
                                ),
                            )
                        )

    result.metadata["rules_evaluated"] = len(rules)
    result.metadata["files_in_diff"] = len(changed_files)
    return result
