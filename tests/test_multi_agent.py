"""Track 7 A3 — multi-agent spawn, AppState projection, permission per agent."""

from __future__ import annotations

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    AGENT_SPAWNED,
    AGENT_SPAWN_REQUEST,
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


def _wire_stack(bus: EventBus) -> AppStateStore:
    permission = PermissionService(bus)
    permission.wire_bus_handlers()

    def approve(event) -> None:
        if not event.payload.get("interactive"):
            return
        bus.publish(
            PERMISSION_CHECK_RESULT,
            {
                "check_id": event.payload["check_id"],
                "granted": True,
                "permissions": list(event.payload.get("permissions") or []),
                "actor_type": event.payload.get("actor_type", "agent"),
                "actor_id": event.payload.get("actor_id"),
            },
            source="ui",
        )

    bus.subscribe(PERMISSION_CHECK_REQUEST, approve)

    registry = ToolRegistry()
    registry.register_tool(
        ToolSpec(name="shell", description="demo shell", handler=_demo_shell_tool)
    )
    ToolRegistryService(bus, registry=registry).start()
    ToolExecutorService(bus, registry).start()
    CommandRouterService(bus).start()
    AgentRuntimeService(bus).start()
    return AppStateStore(bus)


def test_multi_agent_demo_spawns_concurrent_agents() -> None:
    bus = EventBus()
    store = _wire_stack(bus)

    spawn_requests: list[dict] = []
    terminated: list[dict] = []
    bus.subscribe(AGENT_SPAWN_REQUEST, lambda e: spawn_requests.append(dict(e.payload)))
    bus.subscribe(AGENT_TERMINATED, lambda e: terminated.append(dict(e.payload)))

    bus.publish(UI_COMMAND, {"text": "agents: demo", "workspace_id": "ws-multi"}, source="ui")

    assert len(spawn_requests) == 2
    roles = {str(p.get("spawn_role")) for p in spawn_requests}
    assert roles == {"research", "review"}
    assert all(p.get("workspace_id") == "ws-multi" for p in spawn_requests)
    assert len(terminated) == 2
    assert not any(t.get("error") for t in terminated)

    snap = store.snapshot
    assert len(snap.agent_runs) == 2
    assert len(snap.active_agent_run_ids) == 0
    run_roles = {r.spawn_role for r in snap.agent_runs}
    assert run_roles == {"research", "review"}
    assert all(r.workspace_id == "ws-multi" for r in snap.agent_runs)


def test_spawn_role_commands_are_isolated() -> None:
    bus = EventBus()
    store = _wire_stack(bus)

    tool_invokes: list[dict] = []
    bus.subscribe(TOOL_INVOKE, lambda e: tool_invokes.append(dict(e.payload)))

    bus.publish(
        UI_COMMAND,
        {"text": "agent: spawn research", "workspace_id": "ws-1"},
        source="ui",
    )
    bus.publish(
        UI_COMMAND,
        {"text": "agent: spawn review", "workspace_id": "ws-1"},
        source="ui",
    )

    assert len(tool_invokes) == 2
    agent_ids = {inv["agent_id"] for inv in tool_invokes}
    assert len(agent_ids) == 2

    snap = store.snapshot
    assert len(snap.agent_runs) == 2
    roles = {r.spawn_role for r in snap.agent_runs}
    assert roles == {"research", "review"}
    assert all(r.workspace_id == "ws-1" for r in snap.agent_runs)


def test_permission_check_per_agent_spawn() -> None:
    bus = EventBus()
    PermissionService(bus).wire_bus_handlers()
    AgentRuntimeService(bus).start()

    checks: list[dict] = []
    bus.subscribe(PERMISSION_CHECK_REQUEST, lambda e: checks.append(dict(e.payload)))

    bus.publish(
        AGENT_SPAWN_REQUEST,
        {"agent_id": "agent-1", "task": "demo", "request_id": "r1"},
        source="test",
    )
    bus.publish(
        AGENT_SPAWN_REQUEST,
        {"agent_id": "agent-2", "task": "demo", "request_id": "r2"},
        source="test",
    )

    assert len(checks) == 2
    actor_ids = {c["actor_id"] for c in checks}
    assert actor_ids == {"agent-1", "agent-2"}
    assert all(c.get("interactive") is True for c in checks)


def test_command_router_classifies_spawn_and_multi_intents() -> None:
    bus = EventBus()
    routed: list[dict] = []
    bus.subscribe(COMMAND_ROUTED, lambda e: routed.append(dict(e.payload)))
    CommandRouterService(bus).start()

    bus.publish(UI_COMMAND, {"text": "agent: spawn research"}, source="ui")
    bus.publish(UI_COMMAND, {"text": "agents: demo"}, source="ui")

    assert routed[0]["intent"] == INTENT_AGENT
    assert routed[0]["contract_version"] == COMMAND_ROUTED_VERSION
    assert routed[0]["args"]["spawn_role"] == "research"
    assert routed[0]["args"]["spawn_mode"] == "single"

    assert routed[1]["intent"] == INTENT_AGENT
    assert routed[1]["args"]["spawn_mode"] == "multi"
    assert routed[1]["args"]["task"] == "multi-demo"


def test_agent_termination_does_not_affect_sibling_active_state() -> None:
    bus = EventBus()
    store = AppStateStore(bus)

    bus.publish(
        AGENT_SPAWNED,
        {"agent_id": "keep", "request_id": "r-keep", "state": "running"},
        source="test",
    )
    bus.publish(
        AGENT_SPAWNED,
        {"agent_id": "drop", "request_id": "r-drop", "state": "running"},
        source="test",
    )
    bus.publish(
        AGENT_TERMINATED,
        {"agent_id": "drop", "request_id": "r-drop"},
        source="test",
    )

    snap = store.snapshot
    assert snap.active_agent_run_ids == ("keep",)
    assert snap.active_agent_run_id == "keep"
