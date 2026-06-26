#!/usr/bin/env python3
"""Workspace OS Phase 7 gate — Plugin Architecture (v3.5 Part VIII)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Workspace OS Phase 7 Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.workspace import (
        CommandPlugin,
        PluginRegistry,
        TelemetrySnapshot,
        WorkspaceContext,
    )

    def ctx(task: str = "code") -> WorkspaceContext:
        return WorkspaceContext(
            workspace_id="ws-1",
            title="t",
            inferred_task=task,
            active_snapshot=TelemetrySnapshot.empty(now=0.0),
        )

    class P(CommandPlugin):
        def __init__(self, name: str, priority: int, matches: bool, tag: str = "") -> None:
            self._name = name
            self._priority = priority
            self._matches = matches
            self._tag = tag or name

        @property
        def name(self) -> str:
            return self._name

        @property
        def priority(self) -> int:
            return self._priority

        def match(self, context: WorkspaceContext) -> bool:
            return self._matches

        def enrich_context(self, context: WorkspaceContext) -> WorkspaceContext:
            context.metadata["enriched_by"] = self._tag
            return context

        def execute(self, context: WorkspaceContext):
            return f"ran:{self._name}"

    # 1. Tier-1 exclusive matching: highest-priority match wins.
    reg = PluginRegistry([P("low", 10, True), P("high", 90, True), P("nomatch", 99, False)])
    winner = reg.select(ctx())
    if winner is None or winner.name != "high":
        failures.append("highest-priority matching plugin should win")

    # 2. Deterministic tie-break by name when priorities are equal.
    tie = PluginRegistry([P("bbb", 50, True), P("aaa", 50, True)])
    if tie.select(ctx()).name != "aaa":
        failures.append("priority ties should break deterministically by name")

    # 3. No match -> None, and enrich is identity.
    nomatch = PluginRegistry([P("x", 5, False)])
    if nomatch.select(ctx()) is not None:
        failures.append("no matching plugin should yield None")
    base = ctx()
    if nomatch.enrich(base) is not base or "enriched_by" in base.metadata:
        failures.append("enrich with no match must be identity")

    # 4. enrich applies only the winning plugin (enrichment, not fan-out execution).
    enriched = reg.enrich(ctx())
    if enriched.metadata.get("enriched_by") != "high":
        failures.append("enrich should apply the winning plugin only")

    # 5. A plugin raising in match is skipped, not fatal.
    class Boom(P):
        def match(self, context: WorkspaceContext) -> bool:
            raise RuntimeError("bad plugin")

    resilient = PluginRegistry([Boom("boom", 100, True), P("ok", 1, True)])
    if resilient.select(ctx()).name != "ok":
        failures.append("a plugin raising in match must be skipped")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Workspace OS Phase 7 — plugin architecture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
