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
    # Continuity must not depend on object identity: a fresh instance is returned
    # and the previously returned context is left untouched (no hidden aliasing).
    if held is anchor:
        failures.append("retain returned the same object instance (aliasing)")
    if anchor.active_snapshot is not snap or anchor.recent_snapshots:
        failures.append("retain mutated a previously returned WorkspaceContext")

    # After lease expiry, the same transient reading forms a new workspace.
    clock[0] += 61.0
    reformed = resolver2.resolve(transient)
    if reformed.workspace_id == anchor.workspace_id:
        failures.append("expired lease should not retain the old workspace")

    # 6. Max-lease cap — repeated transient renewals cannot outlive the absolute
    # max lifetime; the workspace collapses once the cap is reached.
    cap_clock = [0.0]
    capped = WorkspaceResolver(
        lease_ttl_seconds=60.0, max_lease_seconds=100.0, clock=lambda: cap_clock[0]
    )
    cap_anchor = capped.resolve(snap, repo_root="/home/dev/ai-command-center")
    transient_cap = TelemetrySnapshot.empty(now=cap_clock[0])
    # Renew within the TTL window; the renewed expiry is capped at the max lifetime.
    cap_clock[0] = 50.0
    if capped.resolve(transient_cap).workspace_id != cap_anchor.workspace_id:
        failures.append("transient reading within max lifetime should retain workspace")
    cap_lease = capped.lease
    if cap_lease is not None and cap_lease.expires_at > 100.0:
        failures.append("lease renewal must not extend past max-lease cap")
    # Past the cap, even a transient reading must form a new workspace.
    cap_clock[0] = 101.0
    if capped.resolve(transient_cap).workspace_id == cap_anchor.workspace_id:
        failures.append("workspace should collapse once max-lease cap is exceeded")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Workspace OS Phase 1 — core domain model + resolver")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
