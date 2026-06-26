"""Memory Architecture (Reference Architecture v3.5, Part IX).

Memory is **workspace-centric**; conversation history is secondary. Primary entities:
workspace history, task history, execution history, file relationships, note
relationships, and user preferences. Purpose: maintain continuity across sessions.

This layer is a pure, immutable in-memory model — persistence (SQLite, etc.) is a
repository concern handled elsewhere. Mutating helpers return new instances.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True, slots=True)
class TaskRecord:
    task_id: str
    summary: str
    timestamp: float


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    action: str
    success: bool
    timestamp: float


@dataclass(frozen=True, slots=True)
class Relationship:
    """A typed link from the workspace to a file or note."""

    target: str
    relation: str = "related"


@dataclass(frozen=True, slots=True)
class WorkspaceMemory:
    """Immutable, workspace-centric memory aggregate.

    ``with_*`` helpers return a new aggregate, so a memory snapshot is never mutated
    in place — a clean fit for immutable-state (EventBus/AppState) integration.
    """

    workspace_id: str
    tasks: tuple[TaskRecord, ...] = field(default_factory=tuple)
    executions: tuple[ExecutionRecord, ...] = field(default_factory=tuple)
    files: tuple[Relationship, ...] = field(default_factory=tuple)
    notes: tuple[Relationship, ...] = field(default_factory=tuple)
    preferences: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    conversation: tuple[str, ...] = field(default_factory=tuple)  # secondary

    def with_task(self, record: TaskRecord) -> "WorkspaceMemory":
        return replace(self, tasks=(*self.tasks, record))

    def with_execution(self, record: ExecutionRecord) -> "WorkspaceMemory":
        return replace(self, executions=(*self.executions, record))

    def with_file(self, relationship: Relationship) -> "WorkspaceMemory":
        return replace(self, files=(*self.files, relationship))

    def with_note(self, relationship: Relationship) -> "WorkspaceMemory":
        return replace(self, notes=(*self.notes, relationship))

    def with_preference(self, key: str, value: str) -> "WorkspaceMemory":
        # Last write wins; keys stay unique and deterministically ordered.
        kept = tuple((k, v) for k, v in self.preferences if k != key)
        merged = tuple(sorted((*kept, (key, value))))
        return replace(self, preferences=merged)

    def preference(self, key: str, default: str | None = None) -> str | None:
        for k, v in self.preferences:
            if k == key:
                return v
        return default


class MemoryStore:
    """Holds per-workspace memory aggregates, keyed by ``workspace_id``."""

    def __init__(self) -> None:
        self._by_workspace: dict[str, WorkspaceMemory] = {}

    def get(self, workspace_id: str) -> WorkspaceMemory:
        return self._by_workspace.get(workspace_id) or WorkspaceMemory(workspace_id)

    def put(self, memory: WorkspaceMemory) -> None:
        self._by_workspace[memory.workspace_id] = memory

    def workspaces(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_workspace))
