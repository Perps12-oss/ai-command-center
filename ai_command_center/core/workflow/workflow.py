"""
Workflow Contract - FROZEN ARCHITECTURE SPECIFICATION

Sequential workflow model. No conditions, loops, branches, retries, or parallelism.

FROZEN: Phase 2 - Workspace OS Integration
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """A single step in a sequential workflow."""

    action_id: UUID
    parameters: dict[str, Any] = field(default_factory=dict)

    # Execution metadata
    step_order: int = 0
    description: str = ""


@dataclass(frozen=True, slots=True)
class Workflow:
    """Sequential workflow."""

    id: UUID
    name: str
    description: str
    steps: list[WorkflowStep]

    # Metadata
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True, slots=True)
class WorkflowExecutionResult:
    """Result of executing a workflow."""

    workflow_id: UUID
    success: bool
    step_results: list[Any]
    failed_step_index: int | None
    error_message: str | None


WORKFLOW_SCHEMA_VERSION = 1


def create_workflow(
    name: str,
    description: str,
    steps: list[WorkflowStep],
    tags: list[str] | None = None,
) -> Workflow:
    """Factory for creating workflows."""
    return Workflow(
        id=uuid4(),
        name=name,
        description=description,
        steps=steps,
        tags=tags or [],
    )
