"""Supervised agent demo — end-to-end bus flow (Track 7)."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    AGENT_SPAWNED,
    AGENT_SPAWN_REQUEST,
    AGENT_TASK_COMPLETE,
    AGENT_TERMINATED,
    COMMAND_ROUTED,
    PERMISSION_CHECK_REQUEST,
    PERMISSION_CHECK_RESULT,
    TOOL_INVOKE,
    UI_COMMAND,
)
from ai_command_center.core.permission.permission_service import PermissionService
from ai_command_center.core.tools import ToolResult, ToolSpec
from ai_command_center.services.agent_runtime_service import AgentRuntimeService
from ai_command_center.services.command_router_service import (
    COMMAND_ROUTED_VERSION,
    CommandRouterService,
    INTENT_AGENT,
)
from ai_command_center.services.tool_executor_service import ToolExecutorService
from ai_command_center.services.tool_registry_service import ToolRegistryService
from ai_command_center.tools.tool_registry import ToolRegistry


def _demo_shell_tool(args: dict) -> ToolResult:
    return ToolResult(success=True, output=str(args.get("command", "ok")))


def _wire_permission(bus: EventBus) -> PermissionService:
    permission = PermissionService(bus)
    permission.wire_bus_handlers()
    return permission


def _auto_approve_interactive(bus: EventBus, *, granted: bool = True) -> None:
    def on_request(event) -> None:
        if not event.payload.get("interactive"):
            return
        bus.publish(
            PERMISSION_CHECK_RESULT,
            {
                "check_id": event.payload["check_id"],
                "granted": granted,
                "permissions": list(event.payload.get("permissions") or []),
                "actor_type": event.payload.get("actor_type", "agent"),
                "actor_id": event.payload.get("actor_id"),
            },
            source="ui",
        )

    bus.subscribe(PERMISSION_CHECK_REQUEST, on_request)


def test_supervised_demo_spawn_requires_permission_and_runs_tool() -> None:
    bus = EventBus()
    permission = _wire_permission(bus)
    _auto_approve_interactive(bus)
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="shell", description="demo shell", handler=_demo_shell_tool)
    )
    ToolRegistryService(bus, registry=registry).start()
    ToolExecutorService(bus, registry, permission_service=permission).start()
    AgentRuntimeService(bus).start()

    permission_checks: list[dict] = []
    tool_invokes: list[dict] = []
    terminated: list[dict] = []

    bus.subscribe(PERMISSION_CHECK_REQUEST, lambda e: permission_checks.append(dict(e.payload)))
    bus.subscribe(TOOL_INVOKE, lambda e: tool_invokes.append(dict(e.payload)))
    bus.subscribe(AGENT_TERMINATED, lambda e: terminated.append(dict(e.payload)))

    bus.publish(
        AGENT_SPAWN_REQUEST,
        {"task": "demo", "request_id": "req-demo-1", "workspace_id": "ws-demo"},
        source="test",
    )

    assert permission_checks
    assert permission_checks[0].get("interactive") is True
    assert {"use_ai", "launch_tool"}.issubset(set(permission_checks[0].get("permissions", [])))
    assert tool_invokes
    assert tool_invokes[0]["tool"] == "shell"
    assert terminated
    assert not terminated[0].get("error")


def test_supervised_demo_multi_tool_loop() -> None:
    bus = EventBus()
    permission = _wire_permission(bus)
    _auto_approve_interactive(bus)
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="shell", description="demo shell", handler=_demo_shell_tool)
    )
    ToolRegistryService(bus, registry=registry).start()
    ToolExecutorService(bus, registry, permission_service=permission).start()
    store = AppStateStore(bus)
    runtime = AgentRuntimeService(bus)
    runtime.start()

    completes: list[dict] = []
    bus.subscribe(AGENT_TASK_COMPLETE, lambda e: completes.append(dict(e.payload)))

    bus.publish(
        AGENT_SPAWN_REQUEST,
        {
            "task": "demo: echo one; echo two; echo three",
            "request_id": "req-multi",
            "agent_id": "agent-multi",
            "workspace_id": "ws-demo",
        },
        source="test",
    )

    assert len(completes) == 3
    snap = store.snapshot
    run = next(r for r in snap.agent_runs if r.agent_id == "agent-multi")
    assert run.steps >= 3


def test_interactive_permission_projects_to_app_state() -> None:
    bus = EventBus()
    store = AppStateStore(bus)

    bus.publish(
        PERMISSION_CHECK_REQUEST,
        {
            "check_id": "chk-1",
            "permissions": ["use_ai", "launch_tool"],
            "actor_type": "agent",
            "actor_id": "agent-x",
            "interactive": True,
            "summary": "Approve agent",
        },
        source="agent_runtime",
    )

    snap = store.snapshot
    assert snap.pending_permission_check is not None
    assert snap.pending_permission_check.check_id == "chk-1"
    assert snap.permission_check_revision == 1

    bus.publish(
        PERMISSION_CHECK_RESULT,
        {"check_id": "chk-1", "granted": True},
        source="ui",
    )
    cleared = store.snapshot
    assert cleared.pending_permission_check is None
    assert cleared.permission_check_revision == 2


def test_supervised_demo_projects_into_app_state() -> None:
    bus = EventBus()
    permission = _wire_permission(bus)
    _auto_approve_interactive(bus)
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="shell", description="demo shell", handler=_demo_shell_tool)
    )
    ToolRegistryService(bus, registry=registry).start()
    ToolExecutorService(bus, registry, permission_service=permission).start()
    store = AppStateStore(bus)
    AgentRuntimeService(bus).start()

    bus.publish(
        AGENT_SPAWN_REQUEST,
        {
            "task": "demo",
            "request_id": "req-demo-2",
            "agent_id": "agent-demo-2",
            "workspace_id": "ws-demo",
        },
        source="test",
    )

    snap = store.snapshot
    assert snap.agent_runs
    run = snap.agent_runs[0]
    assert run.agent_id == "agent-demo-2"
    assert run.state in {"terminated", "failed", "waiting", "running", "spawning"}


def test_agent_command_routes_to_spawn_request() -> None:
    bus = EventBus()
    permission = _wire_permission(bus)
    _auto_approve_interactive(bus)
    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="shell", description="demo shell", handler=_demo_shell_tool)
    )
    ToolRegistryService(bus, registry=registry).start()
    ToolExecutorService(bus, registry, permission_service=permission).start()
    CommandRouterService(bus).start()
    AgentRuntimeService(bus).start()

    spawned: list[dict] = []
    bus.subscribe(AGENT_SPAWNED, lambda e: spawned.append(dict(e.payload)))

    bus.publish(
        UI_COMMAND,
        {"text": "agent: demo", "workspace_id": "ws-demo"},
        source="ui",
    )

    assert spawned
    assert spawned[0]["request_id"]


def test_permission_denied_terminates_agent() -> None:
    bus = EventBus()
    permission = _wire_permission(bus)
    _auto_approve_interactive(bus, granted=False)
    terminated: list[dict] = []
    bus.subscribe(AGENT_TERMINATED, lambda e: terminated.append(dict(e.payload)))
    AgentRuntimeService(bus).start()

    bus.publish(
        AGENT_SPAWN_REQUEST,
        {"task": "hello", "request_id": "req-denied", "agent_id": "agent-denied"},
        source="test",
    )

    assert terminated
    assert terminated[0]["error"] == "permission denied"


def test_command_router_classifies_agent_intent() -> None:
    bus = EventBus()
    routed: list[dict] = []
    bus.subscribe(COMMAND_ROUTED, lambda e: routed.append(dict(e.payload)))
    CommandRouterService(bus).start()

    bus.publish(
        UI_COMMAND, {"text": "agent: inspect vault", "workspace_id": "ws-router"}, source="ui"
    )

    assert routed
    assert routed[0]["intent"] == INTENT_AGENT
    assert routed[0]["contract_version"] == COMMAND_ROUTED_VERSION
    assert routed[0]["args"]["task"] == "inspect vault"
