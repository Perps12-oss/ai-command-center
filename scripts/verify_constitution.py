#!/usr/bin/env python3
"""Constitutional governance gate.

Validates required constitutional authorities exist and checks for obvious source-of-truth duplication.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "PROJECT_CONSTITUTION_V4.md",
    "AGENTS.md",
    "docs/ARCHITECTURE.md",
    "docs/CONTRACTS.md",
    "docs/PHASE_LEDGER.md",
    "governance/constitutional_preflight.md",
    "governance/constitutional_review.md",
    "governance/aer_template.md",
    "governance/amendment_template.md",
    "governance/CONSTITUTIONAL_LEDGER.md",
]

# Domains that should have exactly one canonical owner document.
SOURCE_OF_TRUTH_DOCS = {
    "contracts": ["docs/CONTRACTS.md"],
    "event_topics": ["docs/event_topics.md"],
    "architecture": ["docs/ARCHITECTURE.md"],
    "phase_ledger": ["docs/PHASE_LEDGER.md"],
}


def _exists(rel_path: str) -> bool:
    return (PROJECT_ROOT / rel_path).is_file()


def _find_duplicate_authority_docs() -> list[str]:
    failures: list[str] = []
    md_files = [p.relative_to(PROJECT_ROOT).as_posix() for p in PROJECT_ROOT.rglob("*.md")]

    # Heuristic duplicate checks for common source-of-truth names.
    duplicate_patterns = {
        "contracts": re.compile(r"(^|/)contracts\.md$", re.IGNORECASE),
        "event_topics": re.compile(r"(^|/)event_topics\.md$", re.IGNORECASE),
        "architecture": re.compile(r"(^|/)architecture\.md$", re.IGNORECASE),
        "phase_ledger": re.compile(r"(^|/)phase_ledger\.md$", re.IGNORECASE),
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


def main() -> int:
    print("=== Constitution Governance Gate ===")
    failures: list[str] = []

    for rel_path in REQUIRED_FILES:
        if not _exists(rel_path):
            failures.append(f"missing required authority file: {rel_path}")

    failures.extend(_find_duplicate_authority_docs())

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: constitutional authority files present and source-of-truth checks clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
