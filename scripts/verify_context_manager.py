#!/usr/bin/env python3
"""Gate: ContextManager exists and enforces prompt assembly contract."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== ContextManager Gate ===")
    failures: list[str] = []

    from ai_command_center.core.context_manager import (
        ContextManager,
        estimate_tokens,
    )

    mgr = ContextManager(max_context_tokens=1000)
    if mgr.context_budget_tokens != 700:
        failures.append(f"expected budget 700, got {mgr.context_budget_tokens}")

    bundle = mgr.build_context(
        "Summarize this",
        clipboard="Line one\nLine two",
        notes=["# Meeting\nDiscussed roadmap"],
    )
    if "Summarize this" not in bundle.prompt:
        failures.append("query missing from prompt")
    if "clipboard" not in bundle.sources:
        failures.append("clipboard source not attributed")
    if bundle.token_estimate <= 0:
        failures.append("token_estimate must be positive")
    if estimate_tokens("abcd") < 1:
        failures.append("estimate_tokens broken")

    huge = "x" * 10000
    tight = mgr.build_context("short", clipboard=huge, notes=[huge])
    if tight.token_estimate > mgr.context_budget_tokens + 50:
        failures.append("context budget not enforced")

    # OllamaService must not exist yet without using ContextManager (structural check)
    ollama_path = PROJECT_ROOT / "ai_command_center" / "services" / "ollama_service.py"
    if ollama_path.is_file():
        text = ollama_path.read_text(encoding="utf-8")
        if "ContextManager" not in text and "context_manager" not in text:
            failures.append("ollama_service.py must import/use ContextManager")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: ContextManager V1 ready — safe to implement OllamaService")
    print(f"  sources: {bundle.sources}")
    print(f"  token_estimate: {bundle.token_estimate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
