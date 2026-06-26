"""
Workflow Service Contract - FROZEN ARCHITECTURE SPECIFICATION

Sequential workflow execution service. No conditions, loops, branches, retries,
or parallelism at this stage.

FROZEN: Phase 2 - Workspace OS Integration
DO NOT MODIFY without constitutional amendment.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from ai_command_center.core.workflow.workflow import (
    Workflow,
    WorkflowExecutionResult,
)


class WorkflowService(ABC):
    """
    Workflow service contract.
    
    Responsibilities:
    - Create workflows
    - Execute workflows sequentially
    - Retrieve workflows
    - List workflows
    """

    @abstractmethod
    def create(self, workflow: Workflow) -> Workflow:
        """Create a workflow."""
        pass

    @abstractmethod
    def execute(self, workflow_id: UUID) -> WorkflowExecutionResult:
        """Execute a workflow sequentially."""
        pass

    @abstractmethod
    def get(self, workflow_id: UUID) -> Workflow | None:
        """Get workflow by ID."""
        pass

    @abstractmethod
    def list_all(self) -> list[Workflow]:
        """List all workflows."""
        pass
