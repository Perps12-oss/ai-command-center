"""Plan Graph — structured goal-to-action DAG for the Planner layer.

This module defines the canonical structures for representing plans as directed
acyclic graphs (DAGs). The Plan Graph is the primary output of the Planner
and the primary input to the Runtime.

Per ACC Planner Constitution Phase C0:
- 03_PLAN_GRAPH_SPECIFICATION.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(Enum):
    """Plan graph node types."""

    OBJECTIVE = "objective"
    TASK = "task"
    ACTION = "action"


class EdgeType(Enum):
    """Plan graph edge types."""

    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    CONTAINS = "contains"
    ENHANCES = "enhances"


class Priority(Enum):
    """Task/objectives priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class RiskLevel(Enum):
    """Action risk levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FailurePropagation(Enum):
    """Failure propagation behavior for edges."""

    FAIL = "fail"
    CANCEL = "cancel"
    SKIP = "skip"
    CONTINUE = "continue"


@dataclass(frozen=True, slots=True)
class NodeMetadata:
    """Optional metadata for a graph node."""

    tags: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tags": list(self.tags),
            "notes": self.notes,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NodeMetadata:
        return cls(
            tags=tuple(str(t) for t in data.get("tags") or []),
            notes=str(data.get("notes", "")),
            source=str(data.get("source", "")),
        )


@dataclass(frozen=True, slots=True)
class ObjectiveNode:
    """Top-level goal representation in the plan graph.

    An Objective represents a discrete outcome contributing to the goal.
    """

    node_id: str
    label: str
    description: str = ""
    priority: Priority = Priority.NORMAL
    deadline: str = ""  # ISO8601
    success_criteria: tuple[str, ...] = field(default_factory=tuple)
    child_task_refs: tuple[str, ...] = field(default_factory=tuple)
    status: str = "pending"
    metadata: NodeMetadata = field(default_factory=NodeMetadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": NodeType.OBJECTIVE.value,
            "label": self.label,
            "description": self.description,
            "priority": self.priority.value,
            "deadline": self.deadline,
            "success_criteria": list(self.success_criteria),
            "child_task_refs": list(self.child_task_refs),
            "status": self.status,
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObjectiveNode:
        return cls(
            node_id=str(data["node_id"]),
            label=str(data["label"]),
            description=str(data.get("description", "")),
            priority=Priority(data.get("priority", Priority.NORMAL.value)),
            deadline=str(data.get("deadline", "")),
            success_criteria=tuple(str(c) for c in data.get("success_criteria") or []),
            child_task_refs=tuple(str(t) for t in data.get("child_task_refs") or []),
            status=str(data.get("status", "pending")),
            metadata=NodeMetadata.from_dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class TaskNode:
    """Mid-level work unit in the plan graph.

    A Task represents a unit of work contributing to an Objective.
    """

    node_id: str
    objective_ref: str  # References ObjectiveNode.node_id
    label: str
    description: str = ""
    priority: Priority = Priority.NORMAL
    estimated_duration: str = ""  # e.g., "5m", "2h"
    required_capabilities: tuple[str, ...] = field(default_factory=tuple)
    child_action_refs: tuple[str, ...] = field(default_factory=tuple)
    status: str = "pending"
    max_retries: int = 3
    backoff_multiplier: float = 1.5
    can_be_parallelized: bool = False
    rollback_on_failure: bool = True
    metadata: NodeMetadata = field(default_factory=NodeMetadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": NodeType.TASK.value,
            "objective_ref": self.objective_ref,
            "label": self.label,
            "description": self.description,
            "priority": self.priority.value,
            "estimated_duration": self.estimated_duration,
            "required_capabilities": list(self.required_capabilities),
            "child_action_refs": list(self.child_action_refs),
            "status": self.status,
            "max_retries": self.max_retries,
            "backoff_multiplier": self.backoff_multiplier,
            "can_be_parallelized": self.can_be_parallelized,
            "rollback_on_failure": self.rollback_on_failure,
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskNode:
        return cls(
            node_id=str(data["node_id"]),
            objective_ref=str(data["objective_ref"]),
            label=str(data["label"]),
            description=str(data.get("description", "")),
            priority=Priority(data.get("priority", Priority.NORMAL.value)),
            estimated_duration=str(data.get("estimated_duration", "")),
            required_capabilities=tuple(
                str(c) for c in data.get("required_capabilities") or []
            ),
            child_action_refs=tuple(str(a) for a in data.get("child_action_refs") or []),
            status=str(data.get("status", "pending")),
            max_retries=int(data.get("max_retries", 3)),
            backoff_multiplier=float(data.get("backoff_multiplier", 1.5)),
            can_be_parallelized=bool(data.get("can_be_parallelized", False)),
            rollback_on_failure=bool(data.get("rollback_on_failure", True)),
            metadata=NodeMetadata.from_dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class RollbackAction:
    """Definition of a rollback action for an ActionNode."""

    capability: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "parameters": dict(self.parameters),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RollbackAction:
        return cls(
            capability=str(data["capability"]),
            parameters=dict(data.get("parameters") or {}),
        )


@dataclass(frozen=True, slots=True)
class ActionNode:
    """Atomic execution unit in the plan graph.

    An Action represents a single capability invocation.
    """

    node_id: str
    task_ref: str  # References TaskNode.node_id
    capability: str
    parameters: dict[str, Any] = field(default_factory=dict)
    label: str = ""
    description: str = ""
    requires_approval: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    estimated_duration: str = ""  # e.g., "2m"
    rollback_action: RollbackAction | None = None
    status: str = "pending"
    environment: dict[str, str] = field(default_factory=dict)
    secrets: tuple[str, ...] = field(default_factory=tuple)
    metadata: NodeMetadata = field(default_factory=NodeMetadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": NodeType.ACTION.value,
            "task_ref": self.task_ref,
            "capability": self.capability,
            "parameters": dict(self.parameters),
            "label": self.label,
            "description": self.description,
            "requires_approval": self.requires_approval,
            "risk_level": self.risk_level.value,
            "estimated_duration": self.estimated_duration,
            "rollback_action": (
                self.rollback_action.to_dict() if self.rollback_action else None
            ),
            "status": self.status,
            "environment": dict(self.environment),
            "secrets": list(self.secrets),
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionNode:
        rollback = data.get("rollback_action")
        return cls(
            node_id=str(data["node_id"]),
            task_ref=str(data["task_ref"]),
            capability=str(data["capability"]),
            parameters=dict(data.get("parameters") or {}),
            label=str(data.get("label", "")),
            description=str(data.get("description", "")),
            requires_approval=bool(data.get("requires_approval", False)),
            risk_level=RiskLevel(data.get("risk_level", RiskLevel.LOW.value)),
            estimated_duration=str(data.get("estimated_duration", "")),
            rollback_action=RollbackAction.from_dict(rollback) if rollback else None,
            status=str(data.get("status", "pending")),
            environment=dict(data.get("environment") or {}),
            secrets=tuple(str(s) for s in data.get("secrets") or []),
            metadata=NodeMetadata.from_dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    """Dependency relationship between nodes in the plan graph."""

    edge_id: str
    source_node: str
    target_node: str
    edge_type: EdgeType = EdgeType.DEPENDS_ON
    condition: str | None = None  # Optional condition for conditional edges
    on_source_failure: FailurePropagation = FailurePropagation.CANCEL
    on_source_timeout: FailurePropagation = FailurePropagation.SKIP

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "edge_type": self.edge_type.value,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "condition": self.condition,
            "on_source_failure": self.on_source_failure.value,
            "on_source_timeout": self.on_source_timeout.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DependencyEdge:
        return cls(
            edge_id=str(data["edge_id"]),
            source_node=str(data["source_node"]),
            target_node=str(data["target_node"]),
            edge_type=EdgeType(data.get("edge_type", EdgeType.DEPENDS_ON.value)),
            condition=data.get("condition"),
            on_source_failure=FailurePropagation(
                data.get("on_source_failure", FailurePropagation.CANCEL.value)
            ),
            on_source_timeout=FailurePropagation(
                data.get("on_source_timeout", FailurePropagation.SKIP.value)
            ),
        )


@dataclass(frozen=True, slots=True)
class PlanGraphMetadata:
    """Metadata for the entire plan graph."""

    generated_by: str = ""
    confidence: float = 0.0
    model_used: str = ""
    generation_time_ms: int = 0
    planner_mode: str = ""  # "deterministic", "llm_structured", etc.

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_by": self.generated_by,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "generation_time_ms": self.generation_time_ms,
            "planner_mode": self.planner_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanGraphMetadata:
        return cls(
            generated_by=str(data.get("generated_by", "")),
            confidence=float(data.get("confidence", 0.0)),
            model_used=str(data.get("model_used", "")),
            generation_time_ms=int(data.get("generation_time_ms", 0)),
            planner_mode=str(data.get("planner_mode", "")),
        )


@dataclass(frozen=True, slots=True)
class PlanGraph:
    """The top-level plan graph container.

    Represents a complete plan as a directed acyclic graph (DAG) with
    Objectives, Tasks, Actions, and their dependencies.

    Per spec:
    - DAGs CAN branch (multiple outgoing edges)
    - DAGs CAN merge (multiple incoming edges)
    - DAGs CANNOT recurse
    - DAGs CANNOT contain cycles
    """

    graph_id: str
    goal_id: str
    created_at: str  # ISO8601
    objectives: tuple[ObjectiveNode, ...] = field(default_factory=tuple)
    tasks: tuple[TaskNode, ...] = field(default_factory=tuple)
    actions: tuple[ActionNode, ...] = field(default_factory=tuple)
    dependencies: tuple[DependencyEdge, ...] = field(default_factory=tuple)
    version: str = "1.0"
    metadata: PlanGraphMetadata = field(default_factory=PlanGraphMetadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "goal_id": self.goal_id,
            "created_at": self.created_at,
            "version": self.version,
            "objectives": [obj.to_dict() for obj in self.objectives],
            "tasks": [task.to_dict() for task in self.tasks],
            "actions": [action.to_dict() for action in self.actions],
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanGraph:
        return cls(
            graph_id=str(data["graph_id"]),
            goal_id=str(data["goal_id"]),
            created_at=str(data["created_at"]),
            version=str(data.get("version", "1.0")),
            objectives=tuple(
                ObjectiveNode.from_dict(o) for o in data.get("objectives") or []
            ),
            tasks=tuple(TaskNode.from_dict(t) for t in data.get("tasks") or []),
            actions=tuple(ActionNode.from_dict(a) for a in data.get("actions") or []),
            dependencies=tuple(
                DependencyEdge.from_dict(d) for d in data.get("dependencies") or []
            ),
            metadata=PlanGraphMetadata.from_dict(data.get("metadata") or {}),
        )

    @property
    def total_nodes(self) -> int:
        """Total count of all nodes in the graph."""
        return len(self.objectives) + len(self.tasks) + len(self.actions)

    @property
    def max_depth(self) -> int:
        """Calculate maximum depth of the graph.

        This is a simplified calculation that counts the longest path.
        For full topological analysis, use the execution ordering module.
        """
        # This would require topological sort for accurate calculation
        # For now, return a placeholder
        return len(self.tasks) + 1  # Rough estimate

    def get_node_by_id(self, node_id: str) -> ObjectiveNode | TaskNode | ActionNode | None:
        """Find a node by its ID across all node types."""
        for obj in self.objectives:
            if obj.node_id == node_id:
                return obj
        for task in self.tasks:
            if task.node_id == node_id:
                return task
        for action in self.actions:
            if action.node_id == node_id:
                return action
        return None

    def get_dependencies_for_node(self, node_id: str) -> tuple[DependencyEdge, ...]:
        """Get all dependencies where the given node is the target."""
        return tuple(dep for dep in self.dependencies if dep.target_node == node_id)

    def get_dependents_for_node(self, node_id: str) -> tuple[DependencyEdge, ...]:
        """Get all dependencies where the given node is the source."""
        return tuple(dep for dep in self.dependencies if dep.source_node == node_id)

    def validate(self) -> tuple[bool, list[str]]:
        """Validate the plan graph for structural correctness.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors: list[str] = []

        # Check required fields
        if not self.graph_id:
            errors.append("graph_id is required")
        if not self.goal_id:
            errors.append("goal_id is required")

        # Check for duplicate node IDs
        all_node_ids: set[str] = set()
        for obj in self.objectives:
            if obj.node_id in all_node_ids:
                errors.append(f"Duplicate node_id: {obj.node_id}")
            all_node_ids.add(obj.node_id)
        for task in self.tasks:
            if task.node_id in all_node_ids:
                errors.append(f"Duplicate node_id: {task.node_id}")
            all_node_ids.add(task.node_id)
        for action in self.actions:
            if action.node_id in all_node_ids:
                errors.append(f"Duplicate node_id: {action.node_id}")
            all_node_ids.add(action.node_id)

        # Check that all dependency references exist
        for dep in self.dependencies:
            if dep.source_node not in all_node_ids:
                errors.append(f"Dependency references non-existent source: {dep.source_node}")
            if dep.target_node not in all_node_ids:
                errors.append(f"Dependency references non-existent target: {dep.target_node}")

        # Check for self-loops (explicitly prohibited)
        for dep in self.dependencies:
            if dep.source_node == dep.target_node:
                errors.append(f"Self-loop detected: {dep.source_node}")

        # Note: Full cycle detection would require topological sort
        # This is a simplified check

        return len(errors) == 0, errors
