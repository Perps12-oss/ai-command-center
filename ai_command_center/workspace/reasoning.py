"""AI Reasoning Subsystem (Reference Architecture v3.5, Part X).

AI is a **supporting** subsystem. It does NOT own state, routing, execution, or
persistence. Its responsibilities are summarization, classification, transformation,
planning, and context expansion.

    Inputs : WorkspaceContext, Intent, Retrieved Knowledge
    Outputs: ActionResults, Structured Responses, Suggestions

This layer defines the boundary as types plus an injectable engine; the concrete
model call (e.g. Ollama) is supplied by a higher layer. Nothing here executes actions
or persists anything — outputs are returned for other layers to dispatch.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from ai_command_center.workspace.actions import ActionResult
from ai_command_center.workspace.domain import WorkspaceContext
from ai_command_center.workspace.suggestions import Suggestion


class ReasoningTask(Enum):
    """The bounded set of things AI is allowed to do."""

    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    TRANSFORMATION = "transformation"
    PLANNING = "planning"
    CONTEXT_EXPANSION = "context_expansion"


@dataclass(frozen=True, slots=True)
class ReasoningRequest:
    """Everything the subsystem is given — and nothing it could use to own state."""

    context: WorkspaceContext
    intent: object
    task: ReasoningTask
    retrieved_knowledge: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ReasoningResponse:
    """The only things the subsystem is allowed to produce."""

    structured_response: str = ""
    action_results: tuple[ActionResult, ...] = field(default_factory=tuple)
    suggestions: tuple[Suggestion, ...] = field(default_factory=tuple)


class ReasoningEngine:
    """Boundary interface; concrete model integration is injected by a higher layer."""

    def reason(self, request: ReasoningRequest) -> ReasoningResponse:  # pragma: no cover
        raise NotImplementedError


class CallableReasoningEngine(ReasoningEngine):
    """Adapter wrapping a handler callable, keeping model code out of this layer."""

    def __init__(self, handler: Callable[[ReasoningRequest], ReasoningResponse]) -> None:
        self._handler = handler

    def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        return self._handler(request)
