"""P1-C / P1-D: ACTION_INVOKE receipt boundary + command-tool permission parity."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION
from ai_command_center.core.event_bus import Event, EventBus
from ai_command_center.core.events.topics import (
    ACTION_INVOKE_REQUEST,
    ACTION_INVOKE_RESULT,
    TOOL_FAILED,
    TOOL_INVOKE,
    WORKFLOW_EXECUTION_REQUEST,
)
from ai_command_center.core.entity.entity_bus_handlers import register_entity_bus_handlers
from ai_command_center.core.permission.permission import Permission, PermissionContext
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.tools.tool_registry import ToolRegistry


def test_action_invoke_request_does_not_call_action_registry_invoke() -> None:
    bus = EventBus()
    action_registry = MagicMock()
    action_registry.invoke = MagicMock(side_effect=AssertionError("invoke must not run"))
    action_registry.get_by_type = MagicMock(return_value=[])

    register_entity_bus_handlers(
        bus,
        entity_service=MagicMock(),
        relationship_service=MagicMock(),
        workspace_service=MagicMock(),
        timeline_service=MagicMock(),
        action_registry=action_registry,
    )

    workflows: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    def on_workflow(event: Event) -> None:
        workflows.append(dict(event.payload))

    def on_result(event: Event) -> None:
        results.append(dict(event.payload))

    bus.subscribe(WORKFLOW_EXECUTION_REQUEST, on_workflow)
    bus.subscribe(ACTION_INVOKE_RESULT, on_result)

    rid = uuid4().hex
    bus.publish(
        ACTION_INVOKE_REQUEST,
        {
            "request_id": rid,
            "action_type": "launch",
            "action_name": "Launch URL",
            "parameters": {"url": "https://example.com"},
        },
        source="test",
    )

    action_registry.invoke.assert_not_called()
    assert len(workflows) == 1
    assert workflows[0]["steps"][0]["tool"] == "workspace_open_url"
    assert workflows[0]["steps"][0]["args"]["url"] == "https://example.com"
    assert results and results[0].get("delegated") is True
    assert results[0].get("request_id") == rid


def test_action_invoke_unknown_action_is_rejected_without_side_effects() -> None:
    bus = EventBus()
    action_registry = MagicMock()
    register_entity_bus_handlers(
        bus,
        entity_service=MagicMock(),
        relationship_service=MagicMock(),
        workspace_service=MagicMock(),
        timeline_service=MagicMock(),
        action_registry=action_registry,
    )
    results: list[dict[str, Any]] = []
    bus.subscribe(ACTION_INVOKE_RESULT, lambda e: results.append(dict(e.payload)))
    bus.publish(
        ACTION_INVOKE_REQUEST,
        {
            "request_id": "r1",
            "action_name": "Not A Launch",
            "parameters": {},
        },
        source="test",
    )
    action_registry.invoke.assert_not_called()
    assert results and "error" in results[0]


class _DenyPermission:
    def check(self, permission: str, context: PermissionContext) -> bool:
        return False


class _AllowPermission:
    def check(self, permission: str, context: PermissionContext) -> bool:
        return permission == Permission.LAUNCH_TOOL.value


def _tool_bus_with_permission(permission: Any) -> tuple[EventBus, list[dict[str, Any]]]:
    bus = EventBus()
    registry = ToolRegistry()
    ToolExecutorService(bus, registry, permission_service=permission)._on_load()
    failed: list[dict[str, Any]] = []
    bus.subscribe(TOOL_FAILED, lambda e: failed.append(dict(e.payload)))
    return bus, failed


def test_workspace_execute_command_denied_for_agent_without_permission() -> None:
    bus, failed = _tool_bus_with_permission(_DenyPermission())
    bus.publish(
        TOOL_INVOKE,
        {
            "contract_version": TOOL_CONTRACT_VERSION,
            "invoke_id": "i1",
            "tool": "workspace_execute_command",
            "args": {"command": "echo hi"},
            "actor_type": "agent",
            "actor_id": str(uuid4()),
            "workspace_context": {
                "workspace_id": str(uuid4()),
                "entity_id": str(uuid4()),
            },
        },
        source="test",
    )
    assert failed
    assert failed[0].get("error") == "permission denied"
    assert "workspace_execute_command" in failed[0].get("message", "")


def test_shell_and_workspace_execute_command_share_permission_gate() -> None:
    bus, failed = _tool_bus_with_permission(_DenyPermission())
    for tool in ("shell", "workspace_execute_command"):
        failed.clear()
        bus.publish(
            TOOL_INVOKE,
            {
                "contract_version": TOOL_CONTRACT_VERSION,
                "invoke_id": f"i-{tool}",
                "tool": tool,
                "args": {"command": "echo hi"},
                "actor_type": "agent",
                "workspace_context": {
                    "workspace_id": str(uuid4()),
                    "entity_id": str(uuid4()),
                },
            },
            source="test",
        )
        assert failed and failed[0].get("error") == "permission denied"


def test_workspace_execute_command_allowed_for_user_actor() -> None:
    """User actor remains allowed (same policy as shell)."""
    bus = EventBus()
    registry = ToolRegistry()
    ToolExecutorService(bus, registry, permission_service=_DenyPermission())._on_load()
    failed: list[dict[str, Any]] = []
    completed: list[dict[str, Any]] = []
    from ai_command_center.core.events.topics import TOOL_COMPLETED, TOOL_RESULT

    bus.subscribe(TOOL_FAILED, lambda e: failed.append(dict(e.payload)))
    bus.subscribe(TOOL_COMPLETED, lambda e: completed.append(dict(e.payload)))
    bus.subscribe(TOOL_RESULT, lambda e: completed.append(dict(e.payload)))
    bus.publish(
        TOOL_INVOKE,
        {
            "contract_version": TOOL_CONTRACT_VERSION,
            "invoke_id": "user-1",
            "tool": "workspace_execute_command",
            "args": {"command": "echo hi"},
            "actor_type": "user",
            "interactive_user": True,
        },
        source="test",
    )
    assert not failed or failed[0].get("error") != "permission denied"
