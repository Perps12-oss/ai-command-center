"""Single-active-goal scheduler for Brain v1."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import replace

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    EXECUTION_RUN_REQUEST,
    GOAL_ACTIVATED,
    GOAL_CANCELLED,
    GOAL_COMPLETED,
    GOAL_FAILED,
    GOAL_PAUSED,
    GOAL_RESUMED,
    GOAL_SUBMIT_REQUEST,
    GOAL_SUBMITTED,
    PLAN_FAILED,
    PLAN_GENERATED,
    PLAN_REQUEST,
    TASK_COMPLETED,
    TASK_FAILED,
    TASK_READY,
)
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.goal import Goal, GoalStatus, Priority, Task, TaskStatus
from ai_command_center.repositories.goal_repository import GoalRepository
from ai_command_center.services.base import BaseService

_PRIORITY_ORDER = {
    Priority.CRITICAL: 0,
    Priority.HIGH: 1,
    Priority.NORMAL: 2,
    Priority.LOW: 3,
}


class SingleGoalScheduler(BaseService):
    """Sequential scheduler: one active goal, FIFO priority queue."""

    name = "single_goal_scheduler"

    def __init__(self, bus, repo: GoalRepository) -> None:
        super().__init__(bus)
        self._repo = repo
        self._unsubscribers: list[Callable[[], None]] = []
        self._queue: list[Goal] = []
        self._active_goal: Goal | None = None
        self._active_task_id = ""
        self._paused_goal_id = ""
        self._prebuilt_plans: dict[str, dict] = {}
        self._run_options: dict[str, dict] = {}

    def _on_load(self) -> None:
        self._unsubscribers.extend(
            [
                self._bus.subscribe(GOAL_SUBMIT_REQUEST, self._on_submit_request),
                self._bus.subscribe(PLAN_GENERATED, self._on_plan_generated),
                self._bus.subscribe(PLAN_FAILED, self._on_plan_failed),
                self._bus.subscribe(EXECUTION_RUN_COMPLETE, self._on_execution_complete),
                self._bus.subscribe(EXECUTION_RUN_FAILED, self._on_execution_failed),
                self._bus.subscribe(TASK_COMPLETED, self._on_task_completed),
                self._bus.subscribe(TASK_FAILED, self._on_task_failed),
            ]
        )
        self._recover_queue()

    def _recover_queue(self) -> None:
        """Reload persisted QUEUED and ACTIVE goals from the repository on startup.

        Any goal that was ACTIVE at crash time is downgraded back to QUEUED so
        it will be re-planned cleanly by _activate_next_if_idle.
        """
        recovered = self._repo.list_goals(GoalStatus.QUEUED.value)
        previously_active = self._repo.list_goals(GoalStatus.ACTIVE.value)
        for goal in previously_active:
            downgraded = replace(goal, status=GoalStatus.QUEUED)
            self._repo.save_goal(downgraded)
            recovered.append(downgraded)
        self._queue = sorted(recovered, key=lambda item: _PRIORITY_ORDER[item.priority])
        self._activate_next_if_idle()

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._queue.clear()
        self._active_goal = None
        self._active_task_id = ""
        self._paused_goal_id = ""
        self._prebuilt_plans.clear()
        self._run_options.clear()

    def submit_goal(self, goal: Goal) -> None:
        if self._has_unresolved_dependencies(goal):
            failed = replace(goal, status=GoalStatus.FAILED)
            self._repo.save_goal(failed)
            self._bus.publish(
                GOAL_FAILED,
                {
                    "goal": failed.to_payload(),
                    "error": "unresolved dependencies",
                    "correlation": failed.correlation.to_payload(),
                },
                source=self.name,
            )
            return
        queued = replace(goal, status=GoalStatus.QUEUED)
        self._repo.save_goal(queued)
        self._queue.append(queued)
        self._queue.sort(key=lambda item: _PRIORITY_ORDER[item.priority])
        self._bus.publish(
            GOAL_SUBMITTED,
            {"goal": queued.to_payload(), "correlation": queued.correlation.to_payload()},
            source=self.name,
        )
        self._activate_next_if_idle()

    def pause_goal(self, goal_id: str, correlation: CorrelationContext) -> None:
        if self._active_goal is None or self._active_goal.id != goal_id:
            return
        self._paused_goal_id = goal_id
        self._repo.update_goal_status(goal_id, GoalStatus.PAUSED, correlation)
        self._bus.publish(
            GOAL_PAUSED,
            {"goal_id": goal_id, "correlation": correlation.to_payload()},
            source=self.name,
        )

    def resume_goal(self, goal_id: str, correlation: CorrelationContext) -> None:
        if self._paused_goal_id != goal_id:
            return
        self._paused_goal_id = ""
        self._repo.update_goal_status(goal_id, GoalStatus.ACTIVE, correlation)
        self._bus.publish(
            GOAL_RESUMED,
            {"goal_id": goal_id, "correlation": correlation.to_payload()},
            source=self.name,
        )
        self._publish_plan_request(self._active_goal)

    def cancel_goal(self, goal_id: str, correlation: CorrelationContext) -> None:
        self._queue = [goal for goal in self._queue if goal.id != goal_id]
        if self._active_goal is not None and self._active_goal.id == goal_id:
            self._active_goal = None
        if self._paused_goal_id == goal_id:
            self._paused_goal_id = ""
        self._repo.update_goal_status(goal_id, GoalStatus.CANCELLED, correlation)
        self._bus.publish(
            GOAL_CANCELLED,
            {"goal_id": goal_id, "correlation": correlation.to_payload()},
            source=self.name,
        )
        self._activate_next_if_idle()

    def get_next_task(self, correlation: CorrelationContext) -> Task | None:
        if self._active_goal is None or self._paused_goal_id:
            return None
        task = Task(
            id=uuid.uuid4().hex,
            goal_id=self._active_goal.id,
            title=self._active_goal.title,
            description=self._active_goal.description,
            status=TaskStatus.READY,
            correlation=correlation.with_goal(self._active_goal.id),
        )
        self._active_task_id = task.id
        self._bus.publish(
            TASK_READY,
            {"task": task.to_payload(), "correlation": task.correlation.to_payload()},
            source=self.name,
        )
        return task

    def _on_submit_request(self, event: Event) -> None:
        payload = event.payload
        correlation = CorrelationContext.from_payload(payload)
        goal_id = str(payload.get("goal_id") or uuid.uuid4().hex)
        title = str(payload.get("title") or payload.get("goal") or "").strip()
        if not title:
            return
        priority = _parse_priority(payload.get("priority"))
        if not correlation.correlation_id or correlation.correlation_id == goal_id:
            # Prefer authority request_id as correlation when provided.
            request_id = str(payload.get("request_id") or "").strip()
            if request_id:
                correlation = CorrelationContext(
                    correlation_id=request_id,
                    goal_id=goal_id,
                    action_id=correlation.action_id,
                )
        goal = Goal(
            id=goal_id,
            title=title,
            description=str(payload.get("description") or ""),
            priority=priority,
            depends_on=tuple(str(item) for item in payload.get("depends_on") or ()),
            correlation=correlation.with_goal(goal_id),
        )
        raw_plan = payload.get("plan")
        if isinstance(raw_plan, dict) and raw_plan.get("steps"):
            self._prebuilt_plans[goal_id] = dict(raw_plan)
        options: dict = {
            "auto_approve": bool(payload.get("auto_approve", False)),
        }
        workspace_context = payload.get("workspace_context")
        if isinstance(workspace_context, dict):
            options["workspace_context"] = dict(workspace_context)
        if payload.get("workspace_id"):
            options["workspace_id"] = str(payload.get("workspace_id"))
        snippets = payload.get("workspace_snippets")
        if isinstance(snippets, list):
            options["workspace_snippets"] = [str(s) for s in snippets if str(s).strip()]
        state_context = payload.get("state_context")
        if isinstance(state_context, dict):
            options["state_context"] = dict(state_context)
        if payload.get("planner_mode"):
            options["planner_mode"] = str(payload.get("planner_mode"))
        self._run_options[goal_id] = options
        self.submit_goal(goal)

    def _activate_next_if_idle(self) -> None:
        if self._active_goal is not None or not self._queue:
            return
        goal = replace(self._queue.pop(0), status=GoalStatus.ACTIVE)
        self._active_goal = goal
        self._repo.save_goal(goal)
        self._bus.publish(
            GOAL_ACTIVATED,
            {"goal": goal.to_payload(), "correlation": goal.correlation.to_payload()},
            source=self.name,
        )
        prebuilt = self._prebuilt_plans.pop(goal.id, None)
        if prebuilt is not None:
            # Synthetic plan from ExecutionAuthority — skip PlannerService latency.
            self._bus.publish(
                PLAN_GENERATED,
                {
                    "request_id": goal.correlation.correlation_id,
                    "goal": goal.title,
                    "goal_id": goal.id,
                    "plan": prebuilt,
                    "planner_mode": "synthetic",
                    "correlation": goal.correlation.to_payload(),
                },
                source=self.name,
            )
            return
        self._publish_plan_request(goal)

    def _publish_plan_request(self, goal: Goal | None) -> None:
        if goal is None or self._paused_goal_id:
            return
        options = self._run_options.get(goal.id) or {}
        payload: dict = {
            "request_id": goal.correlation.correlation_id,
            "goal": goal.title,
            "goal_id": goal.id,
            "correlation": goal.correlation.to_payload(),
        }
        if options.get("workspace_id"):
            payload["workspace_id"] = options["workspace_id"]
        workspace_context = options.get("workspace_context")
        if isinstance(workspace_context, dict):
            if workspace_context.get("workspace_id"):
                payload["workspace_id"] = workspace_context["workspace_id"]
            if workspace_context.get("entity_id"):
                payload["entity_id"] = workspace_context["entity_id"]
            if workspace_context.get("entity_type"):
                payload["entity_type"] = workspace_context["entity_type"]
        snippets = options.get("workspace_snippets")
        if isinstance(snippets, list) and snippets:
            payload["workspace_snippets"] = list(snippets)
        state_context = options.get("state_context")
        if isinstance(state_context, dict):
            payload["state_context"] = dict(state_context)
        if options.get("planner_mode"):
            payload["planner_mode"] = options["planner_mode"]
        self._bus.publish(PLAN_REQUEST, payload, source=self.name)

    def _on_plan_generated(self, event: Event) -> None:
        if self._active_goal is None:
            return
        if str(event.payload.get("request_id", "")) != self._active_goal.correlation.correlation_id:
            return
        task = self.get_next_task(self._active_goal.correlation)
        if task is None:
            return
        options = self._run_options.pop(self._active_goal.id, {}) or {}
        run_payload: dict = {
            "run_id": task.id,
            "request_id": self._active_goal.correlation.correlation_id,
            "goal_id": self._active_goal.id,
            "plan": dict(event.payload.get("plan") or {}),
            "auto_approve": bool(options.get("auto_approve", False)),
            "correlation": self._active_goal.correlation.to_payload(),
        }
        workspace_context = options.get("workspace_context")
        if isinstance(workspace_context, dict):
            run_payload["workspace_context"] = workspace_context
        self._bus.publish(EXECUTION_RUN_REQUEST, run_payload, source=self.name)

    def _on_plan_failed(self, event: Event) -> None:
        if self._active_goal is None:
            return
        if str(event.payload.get("request_id", "")) != self._active_goal.correlation.correlation_id:
            return
        goal = self._active_goal
        self._repo.update_goal_status(goal.id, GoalStatus.FAILED, goal.correlation)
        self._bus.publish(
            GOAL_FAILED,
            {
                "goal_id": goal.id,
                "error": str(event.payload.get("error") or "plan failed"),
                "correlation": goal.correlation.to_payload(),
            },
            source=self.name,
        )
        self._active_goal = None
        self._activate_next_if_idle()

    def _on_execution_complete(self, event: Event) -> None:
        if not self._event_matches_active_goal(event):
            return
        self._bus.publish(
            TASK_COMPLETED,
            {
                "task_id": str(event.payload.get("run_id") or ""),
                "goal_id": self._active_goal.id,
                "correlation": self._active_goal.correlation.to_payload(),
            },
            source=self.name,
        )

    def _on_execution_failed(self, event: Event) -> None:
        if not self._event_matches_active_goal(event):
            return
        self._bus.publish(
            TASK_FAILED,
            {
                "task_id": str(event.payload.get("run_id") or ""),
                "goal_id": self._active_goal.id,
                "error": str(event.payload.get("error") or "execution failed"),
                "correlation": self._active_goal.correlation.to_payload(),
            },
            source=self.name,
        )

    def _on_task_completed(self, event: Event) -> None:
        goal_id = str(event.payload.get("goal_id") or "")
        if self._active_goal is None or self._active_goal.id != goal_id:
            return
        goal = self._active_goal
        self._repo.update_goal_status(goal.id, GoalStatus.COMPLETE, goal.correlation)
        self._bus.publish(
            GOAL_COMPLETED,
            {"goal_id": goal.id, "correlation": goal.correlation.to_payload()},
            source=self.name,
        )
        self._active_goal = None
        self._active_task_id = ""
        self._activate_next_if_idle()

    def _on_task_failed(self, event: Event) -> None:
        goal_id = str(event.payload.get("goal_id") or "")
        if self._active_goal is None or self._active_goal.id != goal_id:
            return
        goal = self._active_goal
        self._repo.update_goal_status(goal.id, GoalStatus.FAILED, goal.correlation)
        self._bus.publish(
            GOAL_FAILED,
            {
                "goal_id": goal.id,
                "error": str(event.payload.get("error") or "task failed"),
                "correlation": goal.correlation.to_payload(),
            },
            source=self.name,
        )
        self._active_goal = None
        self._active_task_id = ""
        self._activate_next_if_idle()

    def _has_unresolved_dependencies(self, goal: Goal) -> bool:
        if not goal.depends_on:
            return False
        completed = {item.id for item in self._repo.list_goals(GoalStatus.COMPLETE.value)}
        return any(dep not in completed for dep in goal.depends_on)

    def _event_matches_active_goal(self, event: Event) -> bool:
        if self._active_goal is None:
            return False
        run_id = str(event.payload.get("run_id") or "")
        if run_id and self._active_task_id and run_id != self._active_task_id:
            return False
        correlation = CorrelationContext.from_payload(event.payload)
        if correlation.goal_id:
            return correlation.goal_id == self._active_goal.id
        request_id = str(event.payload.get("request_id") or "")
        return bool(request_id and request_id == self._active_goal.correlation.correlation_id)


def _parse_priority(value: object) -> Priority:
    raw = str(value or Priority.NORMAL.value).strip().lower()
    try:
        return Priority(raw)
    except ValueError:
        return Priority.NORMAL
