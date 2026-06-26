#!/usr/bin/env python3
"""Workspace OS Phase 1 gate — core domain model + Workspace Resolver (v3.5 Part II)."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=== Workspace OS Phase 1 Gate Verification ===")
    failures: list[str] = []

    from ai_command_center.workspace import (
        TelemetrySnapshot,
        WorkspaceContext,
        WorkspaceLease,
        WorkspaceResolver,
    )

    # 1. TelemetrySnapshot is an immutable sensor object.
    snap = TelemetrySnapshot(
        timestamp=100.0,
        target_hwnd=42,
        app_name="Code.exe",
        window_title="resolver.py - ai-command-center",
        clipboard_text="hello",
    )
    try:
        snap.app_name = "tamper"  # type: ignore[misc]
        failures.append("TelemetrySnapshot is not frozen")
    except dataclasses.FrozenInstanceError:
        pass
    if TelemetrySnapshot.empty(now=1.0).target_hwnd != 0:
        failures.append("TelemetrySnapshot.empty() not neutral")

    # 2/3. Resolution is deterministic and evidence-ranked.
    clock = [1000.0]
    resolver = WorkspaceResolver(lease_ttl_seconds=60.0, clock=lambda: clock[0])
    ctx_a = resolver.resolve(snap, repo_root="/home/dev/ai-command-center")
    ctx_b = resolver.resolve(snap, repo_root="/home/dev/ai-command-center")
    if ctx_a.workspace_id != ctx_b.workspace_id:
        failures.append("workspace_id not deterministic for identical evidence")
    if not ctx_a.workspace_id.startswith("ws-"):
        failures.append("workspace_id missing 'ws-' prefix")
    if ctx_a.title != "ai-command-center":
        failures.append(f"unexpected title: {ctx_a.title!r}")
    if ctx_a.metadata.get("confidence") != 0.95:
        failures.append("repository_root evidence should yield 0.95 confidence")
    if not isinstance(ctx_a, WorkspaceContext):
        failures.append("resolve did not return a WorkspaceContext")

    # Different evidence -> different workspace.
    other = resolver.resolve(snap, active_path="/home/dev/notes")
    if other.workspace_id == ctx_a.workspace_id:
        failures.append("distinct evidence collapsed to same workspace_id")

    # 4. Lease lifecycle.
    lease = resolver.lease
    if not isinstance(lease, WorkspaceLease) or not lease.is_active(clock[0]):
        failures.append("lease should be active immediately after resolve")
    if lease is not None and lease.is_active(clock[0] + 61.0):
        failures.append("lease should expire after its TTL")

    # 5. A6 — transient excursion retains the leased workspace.
    resolver2 = WorkspaceResolver(lease_ttl_seconds=60.0, clock=lambda: clock[0])
    anchor = resolver2.resolve(snap, repo_root="/home/dev/ai-command-center")
    transient = TelemetrySnapshot.empty(now=clock[0])
    held = resolver2.resolve(transient)  # no evidence -> low confidence
    if held.workspace_id != anchor.workspace_id:
        failures.append("transient low-evidence reading collapsed the workspace (A6)")
    if held.active_snapshot is not transient:
        failures.append("retained workspace did not hydrate the latest snapshot")
    if not held.recent_snapshots:
        failures.append("retained workspace did not record continuity history")

    # After lease expiry, the same transient reading forms a new workspace.
    clock[0] += 61.0
    reformed = resolver2.resolve(transient)
    if reformed.workspace_id == anchor.workspace_id:
        failures.append("expired lease should not retain the old workspace")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Workspace OS Phase 1 — core domain model + resolver")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
