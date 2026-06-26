"""Workspace Resolver (Reference Architecture v3.5, Part II).

Transforms a telemetry reading plus evidence hints into a stable work session.
Resolution is fully deterministic — same evidence always yields the same
``workspace_id`` (A5, Determinism Before AI). A lease keeps the active workspace
stable when the user briefly switches to a low-evidence context (A6, Context
Persistence). Lease renewal is bounded by an absolute maximum lifetime so a
continuous stream of transient readings cannot keep a workspace alive forever.

Every ``resolve`` call returns a fresh ``WorkspaceContext``; continuity is carried
by a stable ``workspace_id``, the lease, and copied semantic state — never by a
shared mutable object. This avoids hidden aliasing and suits an immutable-state
(EventBus/AppState) architecture.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path

from ai_command_center.workspace.domain import (
    TelemetrySnapshot,
    WorkspaceContext,
    WorkspaceLease,
)

# Evidence sources, strongest first, with the confidence each implies.
_EVIDENCE_CONFIDENCE: dict[str, float] = {
    "repository_root": 0.95,
    "active_folder": 0.80,
    "obsidian_vault": 0.70,
    "telemetry": 0.40,
    "none": 0.0,
}

_PATH_SOURCES = frozenset({"repository_root", "active_folder", "obsidian_vault"})


class WorkspaceResolver:
    """Deterministic telemetry -> WorkspaceContext resolver with lease continuity."""

    # Below this confidence a reading is treated as a transient excursion and
    # the active leased workspace is retained rather than collapsed.
    transient_threshold: float = 0.50

    def __init__(
        self,
        *,
        lease_ttl_seconds: float = 300.0,
        max_lease_seconds: float | None = 3600.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._ttl = lease_ttl_seconds
        self._max_lease = max_lease_seconds
        self._clock = clock
        self._lease: WorkspaceLease | None = None
        self._anchor: WorkspaceContext | None = None
        self._anchor_created_at: float | None = None

    @property
    def lease(self) -> WorkspaceLease | None:
        return self._lease

    def resolve(
        self,
        snapshot: TelemetrySnapshot,
        *,
        repo_root: str | Path | None = None,
        active_path: str | Path | None = None,
        vault_path: str | Path | None = None,
        recent_files: Sequence[str] = (),
    ) -> WorkspaceContext:
        evidence, source, confidence = self._strongest_evidence(
            snapshot, repo_root, active_path, vault_path
        )
        now = self._clock()

        if (
            confidence < self.transient_threshold
            and self._anchor is not None
            and self._lease is not None
            and self._lease.is_active(now)
        ):
            return self._retain_anchor(snapshot, now)

        workspace_id = self._workspace_id(evidence)
        context = WorkspaceContext(
            workspace_id=workspace_id,
            title=self._title(evidence, source, snapshot),
            inferred_task=self._inferred_task(snapshot),
            active_snapshot=snapshot,
            active_files=list(recent_files),
            metadata={"evidence_source": source, "confidence": confidence},
        )
        self._anchor_created_at = now
        self._lease = WorkspaceLease(
            workspace_id=workspace_id,
            confidence=confidence,
            expires_at=self._capped_expiry(now, created_at=now),
        )
        self._anchor = self._clone(context)
        return context

    def _retain_anchor(self, snapshot: TelemetrySnapshot, now: float) -> WorkspaceContext:
        # Continuity is carried by workspace_id + lease + copied state, never by
        # mutating a previously returned object: each cycle yields a fresh context.
        anchor = self._anchor
        assert anchor is not None and self._lease is not None
        history = [*anchor.recent_snapshots, repr(anchor.active_snapshot.timestamp)][-10:]
        renewed = WorkspaceContext(
            workspace_id=anchor.workspace_id,
            title=anchor.title,
            inferred_task=anchor.inferred_task,
            active_snapshot=snapshot,
            active_files=list(anchor.active_files),
            recent_snapshots=history,
            memory_refs=list(anchor.memory_refs),
            metadata=dict(anchor.metadata),
        )
        assert self._anchor_created_at is not None
        self._lease = replace(
            self._lease,
            expires_at=self._capped_expiry(now, created_at=self._anchor_created_at),
        )
        self._anchor = self._clone(renewed)
        return renewed

    @staticmethod
    def _clone(context: WorkspaceContext) -> WorkspaceContext:
        # Independent copy: stored anchor and returned context never share mutable
        # state, so a caller mutating one can never corrupt the other.
        return replace(
            context,
            active_files=list(context.active_files),
            recent_snapshots=list(context.recent_snapshots),
            memory_refs=list(context.memory_refs),
            metadata=dict(context.metadata),
        )

    def _capped_expiry(self, now: float, *, created_at: float) -> float:
        # Renew for one TTL, but never past the workspace's absolute max lifetime.
        # The anchor's creation time is passed in explicitly so the cap never
        # depends on instance-attribute assignment order at the call site.
        target = now + self._ttl
        if self._max_lease is not None:
            target = min(target, created_at + self._max_lease)
        return target

    @staticmethod
    def _strongest_evidence(
        snapshot: TelemetrySnapshot,
        repo_root: str | Path | None,
        active_path: str | Path | None,
        vault_path: str | Path | None,
    ) -> tuple[str, str, float]:
        if repo_root:
            return str(repo_root), "repository_root", _EVIDENCE_CONFIDENCE["repository_root"]
        if active_path:
            return str(active_path), "active_folder", _EVIDENCE_CONFIDENCE["active_folder"]
        if vault_path:
            return str(vault_path), "obsidian_vault", _EVIDENCE_CONFIDENCE["obsidian_vault"]
        app = snapshot.app_name.strip()
        title = snapshot.window_title.strip()
        if app or title:
            return f"{app}|{title}", "telemetry", _EVIDENCE_CONFIDENCE["telemetry"]
        return "unknown", "none", _EVIDENCE_CONFIDENCE["none"]

    @staticmethod
    def _workspace_id(evidence: str) -> str:
        digest = hashlib.sha1(evidence.encode("utf-8")).hexdigest()[:12]
        return f"ws-{digest}"

    @staticmethod
    def _title(evidence: str, source: str, snapshot: TelemetrySnapshot) -> str:
        if source in _PATH_SOURCES:
            return Path(evidence).name or evidence
        return (
            snapshot.app_name.strip()
            or snapshot.window_title.strip()
            or "Untitled Workspace"
        )

    @staticmethod
    def _inferred_task(snapshot: TelemetrySnapshot) -> str:
        return snapshot.window_title.strip() or snapshot.app_name.strip() or "general"
