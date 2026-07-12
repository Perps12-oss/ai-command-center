"""Tests for TaskGraph."""

import pytest

from ai_command_center.orchestration.goals.task import Task, TaskStatus
from ai_command_center.orchestration.goals.task_graph import CycleError, TaskGraph


@pytest.fixture
def graph():
    """Create a basic task graph."""
    return TaskGraph(goal_id="goal-1")


@pytest.fixture
def tasks():
    """Create sample tasks."""
    return [
        Task(id="task-1", goal_id="goal-1", title="Task 1"),
        Task(id="task-2", goal_id="goal-1", title="Task 2"),
        Task(id="task-3", goal_id="goal-1", title="Task 3"),
    ]


class TestTaskGraph:
    """Tests for TaskGraph."""

    def test_add_task(self, graph, tasks):
        """add_task adds a task to the graph."""
        result = graph.add_task(tasks[0])
        assert "task-1" in result.tasks
        assert result.tasks["task-1"].title == "Task 1"

    def test_add_duplicate_task_raises(self, graph, tasks):
        """Adding duplicate task raises ValueError."""
        graph = graph.add_task(tasks[0])
        with pytest.raises(ValueError, match="already exists"):
            graph.add_task(tasks[0])

    def test_get_task(self, graph, tasks):
        """get_task returns a task by ID."""
        graph = graph.add_task(tasks[0])
        task = graph.get_task("task-1")
        assert task is not None
        assert task.title == "Task 1"

    def test_add_dependency(self, graph, tasks):
        """add_dependency creates a dependency between tasks."""
        graph = graph.add_task(tasks[0]).add_task(tasks[1])
        graph = graph.add_dependency("task-2", "task-1")  # task-2 depends on task-1

        # task-1 has task-2 as a dependent
        assert "task-2" in graph.dependents["task-1"]
        # task-2 has task-1 as a dependency
        assert "task-1" in graph.dependencies["task-2"]

    def test_self_dependency_raises(self, graph, tasks):
        """A task cannot depend on itself."""
        graph = graph.add_task(tasks[0])
        with pytest.raises(ValueError, match="cannot depend on itself"):
            graph.add_dependency("task-1", "task-1")

    def test_cycle_detection(self, graph, tasks):
        """Adding a cycle raises CycleError."""
        graph = (
            graph.add_task(tasks[0])
            .add_task(tasks[1])
            .add_task(tasks[2])
        )
        # Create: task-1 -> task-2 -> task-3
        graph = graph.add_dependency("task-2", "task-1")
        graph = graph.add_dependency("task-3", "task-2")

        # Trying to add task-1 -> task-3 would create a cycle
        with pytest.raises(CycleError):
            graph.add_dependency("task-1", "task-3")

    def test_get_ready_tasks_no_dependencies(self, graph, tasks):
        """Tasks with no dependencies are ready."""
        graph = (
            graph.add_task(tasks[0])
            .add_task(tasks[1])
            .add_task(tasks[2])
        )
        ready = list(graph.get_ready_tasks())
        assert len(ready) == 3

    def test_get_ready_tasks_with_dependencies(self, graph, tasks):
        """Tasks with incomplete dependencies are not ready."""
        graph = (
            graph.add_task(tasks[0])
            .add_task(tasks[1])
            .add_task(tasks[2])
        )
        graph = graph.add_dependency("task-2", "task-1")
        graph = graph.add_dependency("task-3", "task-2")

        ready = list(graph.get_ready_tasks())
        assert len(ready) == 1
        assert ready[0].id == "task-1"

    def test_get_ready_tasks_with_completed_dependencies(self, graph, tasks):
        """Tasks become ready when dependencies complete."""
        graph = (
            graph.add_task(tasks[0])
            .add_task(tasks[1])
            .add_task(tasks[2])
        )
        graph = graph.add_dependency("task-2", "task-1")
        graph = graph.add_dependency("task-3", "task-2")

        # Mark task-1 as completed
        completed_task_1 = tasks[0].complete()
        graph = graph.with_task_update("task-1", completed_task_1)

        ready = list(graph.get_ready_tasks())
        assert len(ready) == 1
        assert ready[0].id == "task-2"

    def test_execution_order(self, graph, tasks):
        """get_execution_order returns correct grouping."""
        graph = (
            graph.add_task(tasks[0])
            .add_task(tasks[1])
            .add_task(tasks[2])
        )
        graph = graph.add_dependency("task-2", "task-1")
        graph = graph.add_dependency("task-3", "task-2")

        # When all tasks are already completed, they're all in one level
        for t in tasks:
            graph = graph.with_task_update(t.id, t.complete())

        order = graph.get_execution_order()
        # All completed tasks are in a single level
        assert len(order) == 1
        assert set(order[0]) == {"task-1", "task-2", "task-3"}

    def test_completion_percentage_empty(self, graph):
        """Empty graph is 100% complete."""
        assert graph.completion_percentage == 100.0

    def test_completion_percentage_partial(self, graph, tasks):
        """completion_percentage calculates correctly."""
        graph = graph.add_task(tasks[0]).add_task(tasks[1])
        graph = graph.with_task_update("task-1", tasks[0].complete())

        assert graph.completion_percentage == 50.0

    def test_is_complete(self, graph, tasks):
        """is_complete returns True when all tasks are terminal."""
        graph = graph.add_task(tasks[0]).add_task(tasks[1])
        graph = graph.with_task_update("task-1", tasks[0].complete())
        assert not graph.is_complete

        graph = graph.with_task_update("task-2", tasks[1].complete())
        assert graph.is_complete
