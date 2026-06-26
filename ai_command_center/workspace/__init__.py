"""Workspace OS domain layer (Reference Architecture v3.5, Phase 1).

Core domain model + Workspace Resolver. Pure, deterministic, dependency-free:
no EventBus, no repositories, no telemetry acquisition. Higher phases wire these
objects into services.
"""

from ai_command_center.workspace.domain import (
    TelemetrySnapshot,
    WorkspaceContext,
    WorkspaceLease,
)
from ai_command_center.workspace.resolver import WorkspaceResolver

__all__ = [
    "TelemetrySnapshot",
    "WorkspaceContext",
    "WorkspaceLease",
    "WorkspaceResolver",
]
