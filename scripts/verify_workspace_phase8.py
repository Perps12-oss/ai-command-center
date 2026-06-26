#!/usr/bin/env python3
"""Workspace OS Phase 8 gate — Memory Architecture (v3.5 Part IX)."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Workspace OS Phase 8 Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.workspace import (
        ExecutionRecord,
        MemoryStore,
        Relationship,
        TaskRecord,
        WorkspaceMemory,
    )

    # 1. WorkspaceMemory is immutable; with_* returns a new instance (no mutation).
    base = WorkspaceMemory(workspace_id="ws-1")
    try:
        base.workspace_id = "ws-x"  # type: ignore[misc]
        failures.append("WorkspaceMemory must be frozen")
    except dataclasses.FrozenInstanceError:
        pass

    updated = base.with_task(TaskRecord("t1", "do thing", 1.0))
    if updated is base or base.tasks != () or len(updated.tasks) != 1:
        failures.append("with_task must return a new instance without mutating base")

    # 2. All primary workspace-centric entities are supported.
    full = (
        base.with_task(TaskRecord("t1", "task", 1.0))
        .with_execution(ExecutionRecord("open_file", True, 2.0))
        .with_file(Relationship("/repo/a.py", "edited"))
        .with_note(Relationship("note://x", "linked"))
        .with_preference("theme", "dark")
    )
    if not (full.tasks and full.executions and full.files and full.notes):
        failures.append("memory should retain task/execution/file/note entities")

    # 3. Conversation history exists but is secondary (separate from primary entities).
    convo = full.__class__(workspace_id="ws-1", conversation=("hi", "there"))
    if convo.conversation != ("hi", "there"):
        failures.append("conversation history should be representable (secondary)")

    # 4. Preferences: last-write-wins, unique keys, deterministic order.
    prefs = base.with_preference("b", "1").with_preference("a", "2").with_preference("b", "9")
    if prefs.preference("b") != "9":
        failures.append("preference last-write-wins failed")
    if [k for k, _ in prefs.preferences] != ["a", "b"]:
        failures.append("preferences should be unique and deterministically ordered")

    # 5. MemoryStore keyed by workspace_id; continuity across sessions.
    store = MemoryStore()
    if store.get("ws-2").workspace_id != "ws-2":
        failures.append("store.get should return empty memory for unknown workspace")
    store.put(full)
    if store.get("ws-1").preference("theme") != "dark":
        failures.append("store should persist and return workspace memory")
    if store.workspaces() != ("ws-1",):
        failures.append("store.workspaces should list known workspaces")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Workspace OS Phase 8 — memory architecture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
