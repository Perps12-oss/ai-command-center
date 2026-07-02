#!/usr/bin/env python3
"""Constitutional governance gate.

Validates required constitutional authorities exist and checks for obvious
source-of-truth duplication and UI layer import violations.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "PROJECT_CONSTITUTION_V4.md",
    "AGENTS.md",
    "docs/ARCHITECTURE.md",
    "docs/ARCHITECTURE_ENFORCEMENT.md",
    "governance/constitutional_preflight.md",
    "governance/constitutional_review.md",
    "governance/aer_template.md",
    "governance/amendment_template.md",
    "governance/CONSTITUTIONAL_LEDGER.md",
    "ai_command_center/core/contracts.py",
    "ai_command_center/core/events/topics.py",
]

SOURCE_OF_TRUTH_DOCS = {
    "architecture": ["docs/ARCHITECTURE.md"],
}

UI_ROOT = PROJECT_ROOT / "ai_command_center" / "ui"

FORBIDDEN_UI_IMPORT_PREFIXES = (
    "ai_command_center.repositories.",
    "ai_command_center.db.",
    "ai_command_center.services.",
)

SHELL_TRUE_ALLOWLIST = {
    "ai_command_center/services/tool_executor_service.py",
    "ai_command_center/core/workspace_os_actions.py",
}


def _exists(rel_path: str) -> bool:
    return (PROJECT_ROOT / rel_path).is_file()


def _find_duplicate_authority_docs() -> list[str]:
    failures: list[str] = []
    md_files = [p.relative_to(PROJECT_ROOT).as_posix() for p in PROJECT_ROOT.rglob("*.md")]
    duplicate_patterns = {
        "architecture": re.compile(r"(^|/)architecture\.md$", re.IGNORECASE),
    }
    for domain, pattern in duplicate_patterns.items():
        matches = [p for p in md_files if pattern.search(p)]
        canonical = set(SOURCE_OF_TRUTH_DOCS[domain])
        non_canonical = [p for p in matches if p not in canonical]
        if non_canonical:
            failures.append(
                f"{domain}: non-canonical duplicate authority doc(s): {', '.join(sorted(non_canonical))}"
            )
    return failures


def _check_ui_layer_imports() -> list[str]:
    failures: list[str] = []
    if not UI_ROOT.is_dir():
        return failures
    for path in UI_ROOT.rglob("*.py"):
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:
            failures.append(f"ui syntax error: {rel}: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name
                    if mod.startswith(FORBIDDEN_UI_IMPORT_PREFIXES):
                        failures.append(f"ui layer violation: {rel} imports {mod}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if mod.startswith(FORBIDDEN_UI_IMPORT_PREFIXES):
                    failures.append(f"ui layer violation: {rel} imports from {mod}")
    return failures


def _check_shell_true() -> list[str]:
    failures: list[str] = []
    for path in (PROJECT_ROOT / "ai_command_center").rglob("*.py"):
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        if "shell=True" in text and rel not in SHELL_TRUE_ALLOWLIST:
            failures.append(f"shell=True outside allowlist: {rel}")
    return failures


def main() -> int:
    print("=== Constitution Governance Gate ===")
    failures: list[str] = []

    for rel_path in REQUIRED_FILES:
        if not _exists(rel_path):
            failures.append(f"missing required authority file: {rel_path}")

    failures.extend(_find_duplicate_authority_docs())
    failures.extend(_check_ui_layer_imports())
    failures.extend(_check_shell_true())

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: constitutional authority files present and governance checks clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
