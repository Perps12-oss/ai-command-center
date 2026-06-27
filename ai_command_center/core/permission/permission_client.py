"""Synchronous permission client that uses the EventBus request/response topic.

This removes the need for services to call PermissionService directly. Each
check publishes ``permission.check.request`` and waits for the matching
``permission.check.result``.
"""

from __future__ import annotations

import threading
import uuid
from typing import Callable

from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.event_bus import (
    PERMISSION_CHECK_REQUEST,
    PERMISSION_CHECK_RESULT,
)
from ai_command_center.core.permission.permission import PermissionContext


class PermissionClient:
    """Request/response wrapper around PermissionService.

    The client is safe to use from multiple threads; each ``check`` call generates
    a unique request ID and waits for the corresponding result event.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._pending: dict[str, tuple[threading.Event, list[bool]]] = {}
        self._lock = threading.Lock()
        self._unsubscribe: Callable[[], None] | None = None

    def _ensure_subscribed(self) -> None:
        if self._unsubscribe is None:
            self._unsubscribe = self._bus.subscribe(
                PERMISSION_CHECK_RESULT, self._on_result
            )

    def close(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _on_result(self, event: Event) -> None:
        request_id = str(event.payload.get("request_id") or "")
        with self._lock:
            pending = self._pending.pop(request_id, None)
        if pending is None:
            return
        check_event, result_holder = pending
        result_holder.append(bool(event.payload.get("allowed", False)))
        check_event.set()

    def check(
        self,
        permission: str,
        context: PermissionContext,
        *,
        timeout: float = 5.0,
    ) -> bool:
        """Check a permission via the EventBus and return the result.

        This is a synchronous, blocking call. It is safe because the EventBus
        invokes handlers synchronously in the publishing thread.
        """
        self._ensure_subscribed()
        request_id = uuid.uuid4().hex
        check_event = threading.Event()
        result_holder: list[bool] = []
        with self._lock:
            self._pending[request_id] = (check_event, result_holder)

        self._bus.publish(
            PERMISSION_CHECK_REQUEST,
            {
                "request_id": request_id,
                "permission": permission,
                "context": {
                    "entity_id": str(context.entity_id) if context.entity_id else None,
                    "entity_type": context.entity_type,
                    "action_id": str(context.action_id) if context.action_id else None,
                    "actor_type": context.actor_type,
                    "actor_id": str(context.actor_id) if context.actor_id else None,
                },
            },
            source="permission_client",
        )

        check_event.wait(timeout=timeout)
        with self._lock:
            self._pending.pop(request_id, None)
        return bool(result_holder and result_holder[0])
