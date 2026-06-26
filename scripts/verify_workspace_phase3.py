#!/usr/bin/env python3
"""Workspace OS Phase 3 gate — Context Acquisition Architecture (v3.5 Part III)."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Workspace OS Phase 3 Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.workspace import (
        AcquiredContext,
        CallableProvider,
        ContextAcquirer,
        ContextFragment,
        ContextProvider,
        ContextSource,
    )

    # 1. Reliability ranking is Clipboard < ... < UI Automation, UI Automation optional.
    order = [
        ContextSource.CLIPBOARD,
        ContextSource.EXPLICIT_INPUT,
        ContextSource.WORKSPACE_INDEX,
        ContextSource.KNOWN_INTEGRATION,
        ContextSource.UI_AUTOMATION,
    ]
    if [int(s) for s in order] != [1, 2, 3, 4, 5]:
        failures.append("acquisition hierarchy ranks are not 1..5 in order")
    if not ContextSource.UI_AUTOMATION.is_optional:
        failures.append("UI Automation must be optional")
    if ContextSource.CLIPBOARD.is_optional:
        failures.append("Clipboard must not be optional")

    # 2. ContextFragment is a frozen value object exposing its reliability rank.
    frag = ContextFragment(key="selection", value="hi", source=ContextSource.CLIPBOARD)
    if frag.rank != 1:
        failures.append("ContextFragment.rank should mirror source reliability")
    try:
        frag.value = "tamper"  # type: ignore[misc]
        failures.append("ContextFragment is not frozen")
    except dataclasses.FrozenInstanceError:
        pass

    # 3. Higher-ranked source supersedes lower-ranked for the same key.
    acquirer = ContextAcquirer(
        [
            CallableProvider(ContextSource.WORKSPACE_INDEX, lambda: {"topic": "from_index"}),
            CallableProvider(ContextSource.CLIPBOARD, lambda: {"topic": "from_clipboard"}),
        ]
    )
    merged = acquirer.acquire()
    if not isinstance(merged, AcquiredContext):
        failures.append("acquire did not return an AcquiredContext")
    if merged.value("topic") != "from_clipboard":
        failures.append("higher-ranked Clipboard should supersede Workspace Index")

    # 4. Distinct keys from multiple sources all survive, ordered by rank then key.
    multi = ContextAcquirer(
        [
            CallableProvider(ContextSource.KNOWN_INTEGRATION, lambda: {"ticket": "ABC-1"}),
            CallableProvider(ContextSource.CLIPBOARD, lambda: {"clip": "text"}),
            CallableProvider(ContextSource.EXPLICIT_INPUT, lambda: {"query": "summarize"}),
        ]
    ).acquire()
    if [f.key for f in multi.fragments] != ["clip", "query", "ticket"]:
        failures.append("merged fragments not ordered by (rank, key)")

    # 5. UI Automation is excluded unless explicitly opted in (no auto-ingestion).
    ui_provider = CallableProvider(ContextSource.UI_AUTOMATION, lambda: {"uia": "tree"})
    optional_acq = ContextAcquirer([ui_provider])
    if "uia" in optional_acq.acquire():
        failures.append("UI Automation should be skipped by default")
    if "uia" not in optional_acq.acquire(include_ui_automation=True):
        failures.append("UI Automation should be included when opted in")

    # 6. A failing provider is isolated; core still produces context and records error.
    class Boom(ContextProvider):
        source = ContextSource.KNOWN_INTEGRATION

        def acquire(self):  # noqa: ANN201
            raise RuntimeError("integration down")

    resilient = ContextAcquirer(
        [Boom(), CallableProvider(ContextSource.CLIPBOARD, lambda: {"clip": "ok"})]
    ).acquire()
    if resilient.value("clip") != "ok":
        failures.append("a failing provider must not block other sources")
    if not resilient.errors or resilient.errors[0][0] is not ContextSource.KNOWN_INTEGRATION:
        failures.append("provider failure should be recorded in errors")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Workspace OS Phase 3 — context acquisition hierarchy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
