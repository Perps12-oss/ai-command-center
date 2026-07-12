"""TaskGraph — Directed Acyclic Graph (DAG) for task execution.

Reference: docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md Section 9.2
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Iterator

from ai_command_center.orchestration.goals.task import Task, TaskStatus


class CycleError(ValueError):
    """Raised when adding an edge would create a cycle in the graph."""

    pass


@dataclass
class TaskGraph:
    """A Directed Acyclic Graph (DAG) for managing task dependencies.

    The TaskGraph ensures tasks are executed in dependency order and
    supports parallel execution where dependencies allow.

    Operations are designed to be immutable - each modification returns
    a new TaskGraph instance.

    Example:
        graph = TaskGraph(goal_id="goal-1")
        graph = graph.add_task(task1)
        graph = graph.add_task(task2)
        graph = graph.add_dependency(task2.id, task1.id)  # task2 depends on task1

        # Execute ready tasks (those with no incomplete dependencies)
        ready = list(graph.get_ready_tasks())
    """

    goal_id: str
    tasks: dict[str, Task] = field(default_factory=dict)
    # Adjacency list: task_id -> set of dependent task IDs
    dependents: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    # Reverse adjacency: task_id -> set of dependency task IDs
    dependencies: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    def add_task(self, task: Task) -> TaskGraph:
        """Return a new TaskGraph with the task added.

        Raises:
            ValueError: If task with same ID already exists
        """
        if task.id in self.tasks:
            raise ValueError(f"Task with ID {task.id} already exists")

        return TaskGraph(
            goal_id=self.goal_id,
            tasks={**self.tasks, task.id: task},
            dependents=defaultdict(set, {k: set(v) for k, v in self.dependents.items()}),
            dependencies=defaultdict(set, {k: set(v) for k, v in self.dependencies.items()}),
        )

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def add_dependency(self, task_id: str, depends_on: str) -> TaskGraph:
        """Return a new TaskGraph with a dependency added.

        The task_id depends on depends_on - meaning depends_on must
        complete before task_id can start.

        Args:
            task_id: The task that has a dependency
            depends_on: The task it depends on

        Raises:
            ValueError: If either task doesn't exist
            CycleError: If adding would create a cycle
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} does not exist")
        if depends_on not in self.tasks:
            raise ValueError(f"Dependency {depends_on} does not exist")
        if task_id == depends_on:
            raise ValueError("A task cannot depend on itself")

        # Check for cycles before adding
        if self._would_create_cycle(task_id, depends_on):
            raise CycleError(f"Adding dependency {depends_on} -> {task_id} would create a cycle")

        new_dependents = defaultdict(set, {k: set(v) for k, v in self.dependents.items()})
        new_dependents[depends_on].add(task_id)

        new_dependencies = defaultdict(set, {k: set(v) for k, v in self.dependencies.items()})
        new_dependencies[task_id].add(depends_on)

        return TaskGraph(
            goal_id=self.goal_id,
            tasks=self.tasks.copy(),
            dependents=new_dependents,
            dependencies=new_dependencies,
        )

    def _would_create_cycle(self, task_id: str, depends_on: str) -> bool:
        """Check if adding a dependency would create a cycle.

        A cycle would occur if depends_on can already reach task_id
        through existing dependencies.
        """
        # BFS from depends_on to see if we can reach task_id
        visited = set()
        queue = deque([depends_on])

        while queue:
            current = queue.popleft()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self.dependencies.get(current, set()))

        return False

    def get_ready_tasks(self) -> Iterator[Task]:
        """Get all tasks that are ready to execute.

        A task is ready if:
        1. It is in PENDING or READY status
        2. All its dependencies are in terminal states (COMPLETED, SKIPPED)
        """
        for task in self.tasks.values():
            if task.status not in {TaskStatus.PENDING, TaskStatus.READY}:
                continue

            # Check if all dependencies are satisfied
            deps = self.dependencies.get(task.id, set())
            if all(
                self.tasks.get(dep_id, Task(id="", goal_id="", title="")).status.is_terminal
                for dep_id in deps
            ):
                yield task

    def get_blocked_tasks(self) -> Iterator[Task]:
        """Get all tasks that are blocked waiting for dependencies."""
        for task in self.tasks.values():
            if task.status not in {TaskStatus.PENDING, TaskStatus.BLOCKED}:
                continue

            deps = self.dependencies.get(task.id, set())
            if any(
                not self.tasks.get(dep_id, Task(id="", goal_id="", title="")).status.is_terminal
                for dep_id in deps
            ):
                yield task

    def get_execution_order(self) -> list[list[str]]:
        """Get tasks grouped by execution level (for parallel execution).

        Returns a list of lists, where each inner list contains task IDs
        that can be executed in parallel (same dependency level).

        Raises:
            CycleError: If the graph contains a cycle
        """
        if not self._is_acyclic():
            raise CycleError("Graph contains a cycle")

        levels: list[list[str]] = []
        completed = set()

        while len(completed) < len(self.tasks):
            # Find all tasks whose dependencies are satisfied
            current_level = []
            for task_id, task in self.tasks.items():
                if task_id in completed:
                    continue

                if task.status.is_terminal:
                    current_level.append(task_id)
                    completed.add(task_id)
                    continue

                deps = self.dependencies.get(task_id, set())
                if all(dep in completed for dep in deps):
                    current_level.append(task_id)

            if not current_level:
                # No progress possible - remaining tasks are blocked
                break

            levels.append(current_level)
            completed.update(current_level)

        return levels

    def _is_acyclic(self) -> bool:
        """Check if the graph is acyclic using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        colors = defaultdict(lambda: WHITE)

        def dfs(node: str) -> bool:
            colors[node] = GRAY
            for dep in self.dependencies.get(node, set()):
                if colors[dep] == GRAY:
                    return False  # Back edge found - cycle
                if colors[dep] == WHITE and not dfs(dep):
                    return False
            colors[node] = BLACK
            return True

        for task_id in self.tasks:
            if colors[task_id] == WHITE:
                if not dfs(task_id):
                    return False

        return True

    def get_dependent_tasks(self, task_id: str) -> set[str]:
        """Get all tasks that depend on the given task."""
        return self.dependents.get(task_id, set()).copy()

    def get_transitive_dependents(self, task_id: str) -> set[str]:
        """Get all tasks that transitively depend on the given task."""
        result: set[str] = set()
        queue = deque(self.dependents.get(task_id, set()))

        while queue:
            current = queue.popleft()
            if current not in result:
                result.add(current)
                queue.extend(self.dependents.get(current, set()))

        return result

    @property
    def completion_percentage(self) -> float:
        """Get the percentage of tasks that are completed."""
        if not self.tasks:
            return 100.0

        completed = sum(1 for t in self.tasks.values() if t.status.is_terminal)
        return (completed / len(self.tasks)) * 100

    @property
    def is_complete(self) -> bool:
        """Return True if all tasks are in terminal states."""
        return all(t.status.is_terminal for t in self.tasks.values())

    def with_task_update(self, task_id: str, new_task: Task) -> TaskGraph:
        """Return a new TaskGraph with an updated task."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} does not exist")

        return TaskGraph(
            goal_id=self.goal_id,
            tasks={**self.tasks, task_id: new_task},
            dependents=self.dependents,
            dependencies=self.dependencies,
        )


__all__ = ["TaskGraph", "CycleError"]
