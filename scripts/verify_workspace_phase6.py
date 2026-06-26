#!/usr/bin/env python3
"""Workspace OS Phase 6 gate — Runtime Lifecycle (v3.5 Part V)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Workspace OS Phase 6 Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.workspace import (
        ActionDispatcher,
        CallableProvider,
        CallableTarget,
        ContextAcquirer,
        ContextSource,
        IntentResolver,
        LifecyclePhase,
        ResolutionCandidate,
        RuntimePipeline,
        SuggestionEngine,
        TextInsertion,
    )

    # Phase order/labels match the architecture (0A,0B,1,2,3,4).
    if [p.label for p in LifecyclePhase] != ["0A", "0B", "1", "2", "3", "4"]:
        failures.append("lifecycle phase labels do not match Part V")

    traceback_text = "Traceback (most recent call last):\nValueError: boom"
    delivered: list[str] = []

    def build_pipeline() -> RuntimePipeline:
        return RuntimePipeline(
            acquirer=ContextAcquirer(
                [CallableProvider(ContextSource.CLIPBOARD, lambda: {"clipboard": traceback_text})]
            ),
            suggestion_engine=SuggestionEngine(),
            resolver=IntentResolver(),
            dispatcher=ActionDispatcher(
                [CallableTarget(TextInsertion, lambda r: delivered.append(r.text) or True)]
            ),
        )

    # 1. High-confidence action-bearing intent runs all phases through Delivery.
    auto = build_pipeline().run(
        (ResolutionCandidate(score=0.95, target=TextInsertion(text="fix"), source="cmd"),)
    )
    if auto.reached is not LifecyclePhase.DELIVERY or not auto.executed:
        failures.append("auto-execute intent should reach Delivery and execute")
    if auto.delivery is None or not auto.delivery.success or delivered != ["fix"]:
        failures.append("auto-execute should dispatch the action to the target")
    if not auto.suggestions:
        failures.append("hydration should produce suggestions from traceback context")
    if "clipboard" not in auto.context:
        failures.append("context acquisition phase should capture clipboard")

    # 2. Ambiguous (suggest-band) intent must NOT silently execute.
    delivered.clear()
    suggest = build_pipeline().run(
        (ResolutionCandidate(score=0.70, target=TextInsertion(text="x"), source="cmd"),)
    )
    if suggest.executed or suggest.delivery is not None:
        failures.append("suggest-band intent must not execute")
    if suggest.reached is not LifecyclePhase.INTENT_RESOLUTION:
        failures.append("suggest-band should stop at Intent Resolution")
    if delivered:
        failures.append("no dispatch should occur for suggest-band intent")

    # 3. Empty candidates -> clarify, no execution, but context/suggestions still ran.
    clarify = build_pipeline().run(())
    if clarify.executed or not clarify.resolution.needs_clarification:
        failures.append("empty candidates should clarify without executing")
    if not clarify.suggestions:
        failures.append("hydration should still run when resolution clarifies")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Workspace OS Phase 6 — runtime lifecycle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
