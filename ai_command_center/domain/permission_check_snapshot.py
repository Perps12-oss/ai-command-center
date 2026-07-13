"""Immutable AppState snapshot for the Permission Check flow.

Consolidates two existing AppState fields into one typed snapshot:
  pending_permission_check   (PermissionCheckItem | None)
  permission_check_revision  (int)

Adds a resolved-check history not available in the raw fields.
Consumers should prefer AppState.permission_snapshot over the raw fields.
The raw fields are retained for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PendingCheck:
    """A single interactive permission check awaiting UI approval."""

    check_id: str = ""
    permissions: tuple[str, ...] = ()
    actor_type: str = "agent"
    actor_id: str = ""
    summary: str = ""


@dataclass(frozen=True, slots=True)
class ResolvedCheck:
    """A permission check that has been approved or denied."""

    check_id: str = ""
    actor_id: str = ""
    granted: bool = False
    summary: str = ""


_MAX_RESOLVED_HISTORY = 20


@dataclass(frozen=True, slots=True)
class PermissionCheckSnapshot:
    """Immutable AppState projection of the permission check flow."""

    pending: PendingCheck | None = None
    revision: int = 0
    resolved: tuple[ResolvedCheck, ...] = ()
    total_requested: int = 0
    total_granted: int = 0
    total_denied: int = 0

    @property
    def has_pending(self) -> bool:
        return self.pending is not None

    @property
    def last_resolved(self) -> ResolvedCheck | None:
        return self.resolved[0] if self.resolved else None
