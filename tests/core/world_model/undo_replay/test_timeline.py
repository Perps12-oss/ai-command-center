"""Tests for Timeline and UndoReplayFramework."""

import pytest

from ai_command_center.core.world_model.undo_replay import (
    ActionType,
    Snapshot,
    Timeline,
    TimelineEntry,
    TimelineStatus,
    UndoResult,
)


class MockStateProvider:
    """Mock state provider for testing."""

    def __init__(self):
        self.goals = {}
        self.tasks = {}
        self.entities = {}
        self.restored_calls = []

    def get_goals(self):
        return [{"id": k, **v} for k, v in self.goals.items()]

    def get_tasks(self):
        return [{"id": k, **v} for k, v in self.tasks.items()]

    def get_entities(self):
        return [{"id": k, **v} for k, v in self.entities.items()]

    def restore_state(self, entity_type, entity_id, state):
        self.restored_calls.append((entity_type, entity_id, state))
        if entity_type == "goal":
            self.goals[entity_id] = state
        elif entity_type == "task":
            self.tasks[entity_id] = state


class TestTimelineEntry:
    """Tests for TimelineEntry."""

    def test_create_entry(self):
        """Entries can be created with required fields."""
        entry = TimelineEntry(
            id="entry-1",
            action_type=ActionType.CREATE,
            entity_type="goal",
            entity_id="goal-1",
        )
        assert entry.id == "entry-1"
        assert entry.action_type == ActionType.CREATE
        assert entry.can_undo

    def test_to_dict(self):
        """Entries serialize to dict correctly."""
        entry = TimelineEntry(
            id="entry-1",
            action_type=ActionType.UPDATE,
            entity_type="task",
            entity_id="task-1",
            before_state={"title": "Old"},
            after_state={"title": "New"},
        )

        data = entry.to_dict()
        assert data["id"] == "entry-1"
        assert data["action_type"] == "update"
        assert data["before_state"] == {"title": "Old"}

    def test_from_dict(self):
        """Entries deserialize from dict correctly."""
        data = {
            "id": "entry-1",
            "action_type": "delete",
            "entity_type": "entity",
            "entity_id": "entity-1",
            "timestamp": "2024-01-01T00:00:00",
        }

        entry = TimelineEntry.from_dict(data)
        assert entry.id == "entry-1"
        assert entry.action_type == ActionType.DELETE


class TestSnapshot:
    """Tests for Snapshot."""

    def test_create_snapshot(self):
        """Snapshots can be created."""
        snapshot = Snapshot(id="snap-1")
        assert snapshot.id == "snap-1"
        assert snapshot.goals == []

    def test_to_json(self):
        """Snapshots serialize to JSON."""
        snapshot = Snapshot(
            id="snap-1",
            goals=[{"id": "goal-1", "title": "Test"}],
        )

        json_str = snapshot.to_json()
        assert "snap-1" in json_str
        assert "goal-1" in json_str

    def test_from_json(self):
        """Snapshots deserialize from JSON."""
        json_str = '{"id": "snap-1", "goals": [{"id": "g1"}], "tasks": [], "entities": [], "timestamp": "2024-01-01T00:00:00"}'

        snapshot = Snapshot.from_json(json_str)
        assert snapshot.id == "snap-1"
        assert len(snapshot.goals) == 1


class TestTimeline:
    """Tests for Timeline."""

    @pytest.fixture
    def timeline(self):
        """Create a timeline for testing."""
        return Timeline()

    @pytest.fixture
    def timeline_with_provider(self):
        """Create a timeline with mock state provider."""
        provider = MockStateProvider()
        return Timeline(state_provider=provider), provider

    def test_initial_state(self, timeline):
        """Timeline starts in idle state."""
        assert timeline.status == TimelineStatus.IDLE
        assert timeline.can_undo is False
        assert timeline.can_redo is False

    def test_record_action(self, timeline):
        """record adds an entry to the timeline."""
        entry = timeline.record(
            action_type=ActionType.CREATE,
            entity_type="goal",
            entity_id="goal-1",
        )

        assert len(timeline.entries) == 1
        assert timeline.entries[0].entity_id == "goal-1"

    def test_record_with_states(self, timeline):
        """record captures before/after states."""
        entry = timeline.record(
            action_type=ActionType.UPDATE,
            entity_type="goal",
            entity_id="goal-1",
            before_state={"title": "Old"},
            after_state={"title": "New"},
        )

        assert entry.before_state == {"title": "Old"}
        assert entry.after_state == {"title": "New"}

    def test_undo_with_no_entries(self, timeline):
        """Undo returns failure when no entries."""
        result = timeline.undo()
        assert result.success is False

    def test_undo_single_entry(self, timeline_with_provider):
        """Undo restores previous state."""
        timeline, provider = timeline_with_provider

        timeline.record(
            action_type=ActionType.UPDATE,
            entity_type="goal",
            entity_id="goal-1",
            before_state={"title": "Old"},
            after_state={"title": "New"},
        )

        assert timeline.can_undo

        result = timeline.undo()

        assert result.success
        assert result.undone_entry is not None
        assert len(provider.restored_calls) == 1

    def test_undo_cannot_undo(self, timeline):
        """Undo respects can_undo flag."""
        timeline.record(
            action_type=ActionType.DELETE,
            entity_type="goal",
            entity_id="goal-1",
            can_undo=False,
        )

        result = timeline.undo()
        assert result.success is False
        assert "cannot be undone" in result.message

    def test_redo_after_undo(self, timeline_with_provider):
        """Redo reapplies after undo."""
        timeline, provider = timeline_with_provider

        timeline.record(
            action_type=ActionType.CREATE,
            entity_type="goal",
            entity_id="goal-1",
            after_state={"title": "New"},
        )

        timeline.undo()
        result = timeline.redo()

        assert result.success
        assert timeline.can_undo
        assert timeline.can_redo is False

    def test_record_clears_redo_history(self, timeline):
        """New recording clears redo history."""
        timeline.record(
            action_type=ActionType.CREATE,
            entity_type="goal",
            entity_id="goal-1",
        )
        timeline.undo()  # Undo the create

        # Record new action
        timeline.record(
            action_type=ActionType.CREATE,
            entity_type="task",
            entity_id="task-1",
        )

        assert timeline.can_redo is False

    def test_create_snapshot(self, timeline_with_provider):
        """create_snapshot captures current state."""
        timeline, provider = timeline_with_provider
        provider.goals["goal-1"] = {"title": "Test Goal"}

        snapshot = timeline.create_snapshot()

        assert snapshot.id is not None
        assert len(snapshot.goals) == 1
        assert snapshot.goals[0]["title"] == "Test Goal"

    def test_get_entries_for_entity(self, timeline):
        """get_entries_for_entity filters correctly."""
        timeline.record(
            action_type=ActionType.CREATE,
            entity_type="goal",
            entity_id="goal-1",
        )
        timeline.record(
            action_type=ActionType.UPDATE,
            entity_type="goal",
            entity_id="goal-1",
        )
        timeline.record(
            action_type=ActionType.CREATE,
            entity_type="task",
            entity_id="task-1",
        )

        goal_entries = timeline.get_entries_for_entity("goal", "goal-1")
        assert len(goal_entries) == 2

        task_entries = timeline.get_entries_for_entity("task", "task-1")
        assert len(task_entries) == 1


class TestUndoResult:
    """Tests for UndoResult."""

    def test_success_result(self):
        """Success results have correct attributes."""
        result = UndoResult(
            success=True,
            message="Undone successfully",
            restored_state={"title": "Old"},
        )
        assert result.success
        assert result.restored_state == {"title": "Old"}

    def test_failure_result(self):
        """Failure results have correct attributes."""
        result = UndoResult(
            success=False,
            message="Nothing to undo",
        )
        assert result.success is False
        assert result.undone_entry is None
