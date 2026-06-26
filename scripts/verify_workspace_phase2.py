#!/usr/bin/env python3
"""Workspace OS Phase 2 gate — Intent Resolution Architecture (v3.5 Part IV)."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Workspace OS Phase 2 Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.workspace import (
        IntentResolution,
        IntentResolver,
        ResolutionCandidate,
        ResolutionMode,
        classify,
    )

    # 1. ResolutionCandidate is a frozen value object (score, target, source).
    cand = ResolutionCandidate(score=0.95, target="open_file", source="command")
    try:
        cand.score = 0.1  # type: ignore[misc]
        failures.append("ResolutionCandidate is not frozen")
    except dataclasses.FrozenInstanceError:
        pass

    # 2. Confidence policy boundaries: >=0.90 auto, [0.50,0.90) suggest, <0.50 clarify.
    policy = {
        0.90: ResolutionMode.AUTO_EXECUTE,
        0.95: ResolutionMode.AUTO_EXECUTE,
        0.899: ResolutionMode.SUGGEST,
        0.50: ResolutionMode.SUGGEST,
        0.499: ResolutionMode.CLARIFY,
        0.0: ResolutionMode.CLARIFY,
    }
    for score, expected in policy.items():
        if classify(score) is not expected:
            failures.append(f"classify({score}) != {expected}")

    resolver = IntentResolver()

    # 3. Empty candidate set -> CLARIFY (no silent execution of ambiguity).
    empty = resolver.resolve([])
    if not isinstance(empty, IntentResolution):
        failures.append("resolve did not return an IntentResolution")
    if empty.mode is not ResolutionMode.CLARIFY or empty.best is not None:
        failures.append("empty candidates should resolve to CLARIFY with no best")
    if not empty.needs_clarification:
        failures.append("empty resolution should report needs_clarification")

    # 4. Deterministic ranking: strongest score wins; ties broken by source.
    candidates = [
        ResolutionCandidate(0.60, "search", "search"),
        ResolutionCandidate(0.92, "run_a", "ztool"),
        ResolutionCandidate(0.92, "run_b", "atool"),  # same score, earlier source
    ]
    first = resolver.resolve(candidates)
    second = resolver.resolve(list(reversed(candidates)))
    if first.best is None or first.best.source != "atool":
        failures.append("tie-break should prefer the lexicographically smaller source")
    if [c.source for c in first.candidates] != [c.source for c in second.candidates]:
        failures.append("ranking is not deterministic across input orderings")
    if not first.should_auto_execute:
        failures.append("top score 0.92 should yield AUTO_EXECUTE")

    # 5. Suggestion band reporting (0.50 <= score < 0.90).
    mixed = resolver.resolve(
        [
            ResolutionCandidate(0.95, "x", "a"),  # auto
            ResolutionCandidate(0.75, "y", "b"),  # suggest
            ResolutionCandidate(0.55, "z", "c"),  # suggest
            ResolutionCandidate(0.20, "w", "d"),  # clarify
        ]
    )
    if [c.source for c in mixed.suggestions] != ["b", "c"]:
        failures.append("suggestions should list only the 0.50-0.90 band, ranked")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Workspace OS Phase 2 — intent resolution + confidence policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
