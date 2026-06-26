#!/usr/bin/env python3
"""Workspace OS Phase 5 gate — Suggestion Engine (v3.5 Part VII)."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Workspace OS Phase 5 Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.workspace import (
        AcquiredContext,
        CallableProvider,
        ContextAcquirer,
        ContextSource,
        Suggestion,
        SuggestionEngine,
        SuggestionRule,
    )

    # 1. Suggestion is a frozen value object.
    s = Suggestion("Explain Error", "explain_error", 0.95)
    try:
        s.score = 0.1  # type: ignore[misc]
        failures.append("Suggestion must be frozen")
    except dataclasses.FrozenInstanceError:
        pass

    engine = SuggestionEngine()

    # 2. Python traceback context yields the expected pre-AI suggestions, ranked.
    traceback_text = (
        "Traceback (most recent call last):\n"
        '  File "x.py", line 1, in <module>\nValueError: boom'
    )
    ctx = ContextAcquirer(
        [CallableProvider(ContextSource.CLIPBOARD, lambda: {"clipboard": traceback_text})]
    ).acquire()
    suggestions = engine.suggest(ctx)
    labels = [s.label for s in suggestions]
    if labels != ["Explain Error", "Create Issue", "Search Notes", "Save Snippet"]:
        failures.append(f"unexpected suggestion ranking: {labels}")

    # 3. Suggestions are pre-AI/deterministic: same context -> identical output.
    if engine.suggest(ctx) != suggestions:
        failures.append("suggestions must be deterministic for identical context")

    # 4. Non-matching context yields no suggestions (avoid AI invocation).
    empty_ctx = ContextAcquirer(
        [CallableProvider(ContextSource.CLIPBOARD, lambda: {"clipboard": "hello world"})]
    ).acquire()
    if engine.suggest(empty_ctx):
        failures.append("non-matching context should yield no suggestions")

    # 5. Custom rules compose and rank by score across rules.
    custom = SuggestionEngine(
        rules=(
            SuggestionRule(
                "always",
                matches=lambda c: True,
                suggestions=(Suggestion("Top", "top", 0.99), Suggestion("Low", "low", 0.10)),
            ),
        )
    )
    out = custom.suggest(AcquiredContext())
    if [s.label for s in out] != ["Top", "Low"]:
        failures.append("custom rule suggestions not ranked by score")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Workspace OS Phase 5 — suggestion engine")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
