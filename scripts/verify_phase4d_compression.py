#!/usr/bin/env python3
"""Phase 4D gate — context compression for long conversations."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Phase 4D Gate Verification (compression) ===")
    failures: list[str] = []

    from ai_command_center.core.context_manager import ContextManager, estimate_tokens

    mgr = ContextManager(max_context_tokens=512, fill_ratio=0.7)
    budget = mgr.context_budget_tokens

    history: list[tuple[str, str]] = []
    for i in range(50):
        history.append(("user", f"Question number {i} about topic {i % 5}"))
        history.append(("assistant", f"Answer number {i} with detail " * 8))

    bundle = mgr.build_context("Follow up", conversation_history=history)
    if bundle.token_estimate > budget + 5:
        failures.append(
            f"bundle {bundle.token_estimate} tokens exceeds budget {budget}"
        )
    if "conversation_summary" not in bundle.sources:
        failures.append("expected conversation_summary in sources after compression")
    if not bundle.prompt:
        failures.append("empty prompt")
    if bundle.version != "1.1":
        failures.append(f"expected bundle version 1.1, got {bundle.version}")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 4D — history compression under token budget")
    print(f"  budget={budget} estimate={bundle.token_estimate}")
    print(f"  sources={list(bundle.sources)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
