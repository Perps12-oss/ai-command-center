"""Workspace OS domain layer (Reference Architecture v3.5).

Phase 1 (Part II): core domain model + Workspace Resolver.
Phase 2 (Part IV): deterministic, classify-only intent resolution.
Phase 3 (Part III): reliability-first, pull-based context acquisition.

Pure, deterministic, dependency-free: no EventBus, no repositories, no background
telemetry acquisition, no execution, no AI. Higher phases wire these objects into
services and inject OS-specific readers.
"""

from ai_command_center.workspace.context_acquisition import (
    AcquiredContext,
    CallableProvider,
    ContextAcquirer,
    ContextFragment,
    ContextProvider,
    ContextSource,
)
from ai_command_center.workspace.domain import (
    TelemetrySnapshot,
    WorkspaceContext,
    WorkspaceLease,
)
from ai_command_center.workspace.intent import (
    AUTO_EXECUTE_THRESHOLD,
    SUGGEST_THRESHOLD,
    IntentResolution,
    IntentResolver,
    ResolutionCandidate,
    ResolutionMode,
    classify,
)
from ai_command_center.workspace.resolver import WorkspaceResolver

__all__ = [
    "TelemetrySnapshot",
    "WorkspaceContext",
    "WorkspaceLease",
    "WorkspaceResolver",
    "ResolutionCandidate",
    "ResolutionMode",
    "IntentResolution",
    "IntentResolver",
    "classify",
    "AUTO_EXECUTE_THRESHOLD",
    "SUGGEST_THRESHOLD",
    "ContextSource",
    "ContextFragment",
    "ContextProvider",
    "CallableProvider",
    "AcquiredContext",
    "ContextAcquirer",
]
