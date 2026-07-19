"""Capability routing domain models (Agent Runtime Interface)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CapabilityKind(str, Enum):
    """User-facing capability slices routed to runtime providers."""

    CHAT = "chat"
    PLANNING = "planning"
    CODING = "coding"
    RESEARCH = "research"
    AUTOMATION = "automation"
    AGENTS = "agents"
    MEMORY = "memory"


class ProviderHealthState(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    state: ProviderHealthState
    detail: str = ""


@dataclass(frozen=True, slots=True)
class RuntimeInvocationRequest:
    """Provider input contract — see AGENT_RUNTIME_INTERFACE.md."""

    request_id: str
    kind: CapabilityKind
    provider_id: str
    query: str
    workspace_id: str = ""
    workspace_entity_id: str = ""
    session_id: str = ""
    context_bundle: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CapabilityDispatch:
    """Envelope published on capability.dispatch."""

    request_id: str
    kind: CapabilityKind
    provider_id: str
    query: str
    fallback_provider_id: str = "native"
    command_payload: dict[str, object] = field(default_factory=dict)
