"""Supervised agent runtime — bus-native spawn/task/terminate (A1 skeleton)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    AGENT_CANCEL_REQUEST,
    AGENT_SPAWNED,
    AGENT_SPAWN_REQUEST,
    AGENT_TASK_COMPLETE,
    AGENT_TASK_REQUEST,
    AGENT_TERMINATED,
    CHAT_COMPLETE,
    TELEMETRY_EVENT,
    UI_COMMAND,
)
from ai_command_center.domain.agent_session import AgentState
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)


class AgentRuntimeService(BaseService):
    """Publishes agent lifecycle events; routes single-task agents via ui.command."""

    name = "agent_runtime"
    _MAX_STEPS = 8

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._active: dict[str, dict[str, object]] = {}

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(AGENT_SPAWN_REQUEST, self._on_spawn_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(AGENT_TASK_REQUEST, self._on_task_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(AGENT_CANCEL_REQUEST, self._on_cancel_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(CHAT_COMPLETE, self._on_chat_complete)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._active.clear()

    def _telemetry(self, name: str, payload: dict[str, object]) -> None:
        self._bus.publish(
            TELEMETRY_EVENT,
            {"name": name, **payload},
            source=self.name,
        )

    def _on_spawn_request(self, event: Event) -> None:
        agent_id = str(event.payload.get("agent_id") or uuid.uuid4().hex)
        request_id = str(event.payload.get("request_id") or uuid.uuid4().hex)
        workspace_id = event.payload.get("workspace_id")
        task = str(event.payload.get("task", "")).strip()
        self._active[agent_id] = {
            "request_id": request_id,
            "task": task,
            "steps": 0,
            "state": AgentState.RUNNING.value,
        }
        self._bus.publish(
            AGENT_SPAWNED,
            {
                "agent_id": agent_id,
                "request_id": request_id,
                "workspace_id": workspace_id,
                "state": AgentState.SPAWNING.value,
            },
            source=self.name,
        )
        _logger.info("agent.spawned agent_id=%s request_id=%s", agent_id, request_id)
        self._telemetry("agent.spawned", {"agent_id": agent_id, "request_id": request_id})
        if task:
            self._bus.publish(
                AGENT_TASK_REQUEST,
                {"agent_id": agent_id, "request_id": request_id, "task": task},
                source=self.name,
            )

    def _on_task_request(self, event: Event) -> None:
        agent_id = str(event.payload.get("agent_id", ""))
        if not agent_id or agent_id not in self._active:
            return
        entry = self._active[agent_id]
        steps = int(entry.get("steps", 0)) + 1
        if steps > self._MAX_STEPS:
            self._terminate(agent_id, error="max agent steps exceeded")
            return
        entry["steps"] = steps
        task = str(event.payload.get("task") or entry.get("task") or "").strip()
        request_id = str(event.payload.get("request_id") or entry.get("request_id") or "")
        if not task:
            self._terminate(agent_id)
            return
        self._bus.publish(
            UI_COMMAND,
            {"text": task, "agent_id": agent_id, "request_id": request_id},
            source=self.name,
        )

    def _on_chat_complete(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id") or "")
        if not request_id:
            return
        for agent_id, entry in list(self._active.items()):
            if str(entry.get("request_id")) != request_id:
                continue
            self._bus.publish(
                AGENT_TASK_COMPLETE,
                {
                    "agent_id": agent_id,
                    "request_id": request_id,
                    "status": "complete",
                },
                source=self.name,
            )
            self._terminate(agent_id)
            break

    def _on_cancel_request(self, event: Event) -> None:
        agent_id = str(event.payload.get("agent_id", ""))
        if agent_id:
            self._terminate(agent_id, error=str(event.payload.get("reason", "cancelled")))

    def _terminate(self, agent_id: str, *, error: str | None = None) -> None:
        entry = self._active.pop(agent_id, None)
        if entry is None:
            return
        request_id = str(entry.get("request_id", ""))
        payload: dict[str, object] = {
            "agent_id": agent_id,
            "request_id": request_id,
            "state": AgentState.TERMINATED.value,
        }
        if error:
            payload["error"] = error
        self._bus.publish(AGENT_TERMINATED, payload, source=self.name)
        self._telemetry("agent.terminated", payload)
