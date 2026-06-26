"""Workspace Resolver (Reference Architecture v3.5, Part II).

Transforms a telemetry reading plus evidence hints into a stable work session.
Resolution is fully deterministic — same evidence always yields the same
``workspace_id`` (A5, Determinism Before AI). A lease keeps the active workspace
stable when the user briefly switches to a low-evidence context (A6, Context
Persistence).
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
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._ttl = lease_ttl_seconds
        self._clock = clock
        self._lease: WorkspaceLease | None = None
        self._anchor: WorkspaceContext | None = None

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
        self._lease = WorkspaceLease(
            workspace_id=workspace_id,
            confidence=confidence,
            expires_at=now + self._ttl,
        )
        self._anchor = context
        return context

    def _retain_anchor(self, snapshot: TelemetrySnapshot, now: float) -> WorkspaceContext:
        anchor = self._anchor
        assert anchor is not None and self._lease is not None
        anchor.recent_snapshots.append(repr(anchor.active_snapshot.timestamp))
        if len(anchor.recent_snapshots) > 10:
            del anchor.recent_snapshots[:-10]
        anchor.active_snapshot = snapshot
        self._lease = replace(self._lease, expires_at=now + self._ttl)
        return anchor

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
        return snapshot.app_name or snapshot.window_title or "Untitled Workspace"

    @staticmethod
    def _inferred_task(snapshot: TelemetrySnapshot) -> str:
        return snapshot.window_title.strip() or snapshot.app_name.strip() or "general"
