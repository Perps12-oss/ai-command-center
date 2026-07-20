"""Layer-1 Workspace OS capability catalog (v1).

Unimplemented capabilities are registered with planner_visible=False so the
syscall table is complete without flooding the planner.
"""

from __future__ import annotations

from ai_command_center.capabilities.definition import CapabilityDefinition

# Seed: wired today via ToolRegistry / EA / orchestrator.
_WIRED: tuple[CapabilityDefinition, ...] = (
    CapabilityDefinition(
        id="notes.create",
        domain="notes",
        description="Create a vault note",
        inputs=("body",),
        outputs=("path",),
        mutates_world_model=True,
        planner_visible=True,
        execution_handler="NotesProvider",
        tags=("notes", "write"),
    ),
    CapabilityDefinition(
        id="notes.search",
        domain="notes",
        description="Search vault notes",
        inputs=("query",),
        outputs=("hits",),
        planner_visible=True,
        execution_handler="NotesProvider",
        tags=("notes", "read"),
    ),
    CapabilityDefinition(
        id="memory.store",
        domain="memory",
        description="Store a memory item",
        inputs=("body",),
        outputs=("memory_id",),
        mutates_world_model=True,
        planner_visible=True,
        execution_handler="MemoryProvider",
        tags=("memory", "write"),
    ),
    CapabilityDefinition(
        id="memory.query",
        domain="memory",
        description="Query stored memories",
        inputs=("query",),
        outputs=("hits",),
        planner_visible=True,
        execution_handler="MemoryProvider",
        tags=("memory", "read"),
    ),
    CapabilityDefinition(
        id="navigate",
        domain="system",
        description="Navigate to a UI view",
        inputs=("view",),
        outputs=("view",),
        planner_visible=True,
        execution_handler="NavigateHandler",
        tags=("ui", "system"),
    ),
    CapabilityDefinition(
        id="applications.launch",
        domain="applications",
        description="Launch a desktop application",
        inputs=("application",),
        outputs=("status",),
        mutates_world_model=True,
        planner_visible=True,
        execution_handler="ApplicationLauncher",
        tags=("applications", "write"),
    ),
    CapabilityDefinition(
        id="llm.chat",
        domain="llm",
        description="Conversational LLM response",
        inputs=("prompt",),
        outputs=("response",),
        planner_visible=True,
        execution_handler="ChatHandler",
        tags=("llm", "reasoning"),
    ),
    CapabilityDefinition(
        id="llm.generate",
        domain="llm",
        description="Generate text from a prompt",
        inputs=("prompt",),
        outputs=("text",),
        planner_visible=True,
        execution_handler="ChatHandler",
        tags=("llm", "reasoning"),
    ),
    CapabilityDefinition(
        id="goals.plan",
        domain="goals",
        description="Plan tasks for a free-text goal",
        inputs=("goal",),
        outputs=("plan",),
        planner_visible=True,
        execution_handler="PlannerService",
        tags=("goals",),
    ),
    CapabilityDefinition(
        id="shell",
        domain="system",
        description="Run an approved shell command",
        inputs=("command",),
        outputs=("stdout",),
        requires_human_approval=True,
        planner_visible=True,
        execution_handler="ShellTool",
        tags=("system",),
    ),
    CapabilityDefinition(
        id="system.noop",
        domain="system",
        description="Idempotent no-op when state already holds",
        inputs=("reason",),
        outputs=("status",),
        planner_visible=False,
        execution_handler="NoOpHandler",
        tags=("system", "idempotency"),
    ),
)

# Domain stubs — visible=False until handlers exist.
_DOMAINS_STUB: dict[str, tuple[str, ...]] = {
    "applications": (
        "close",
        "focus",
        "switch",
        "list_running",
        "install",
        "uninstall",
    ),
    "notes": ("update", "delete", "open", "link", "summarize", "extract_tasks"),
    "memory": ("update", "delete", "relate", "summarize", "preferences"),
    "tasks": (
        "create",
        "update",
        "complete",
        "delete",
        "list",
        "prioritize",
        "schedule",
    ),
    "goals": ("create", "execute", "pause", "resume", "cancel", "review"),
    "calendar": (
        "query",
        "create",
        "update",
        "cancel",
        "availability",
        "reminders",
    ),
    "files": ("search", "open", "move", "copy", "delete", "organize", "summarize"),
    "search": (
        "workspace",
        "notes",
        "memory",
        "files",
        "calendar",
        "tasks",
        "web",
    ),
    "workflow": ("create", "run", "pause", "resume", "stop", "inspect"),
    "automation": ("create", "enable", "disable", "run", "audit"),
    "agent": ("create", "execute", "delegate", "review", "terminate"),
    "communication": (
        "email.send",
        "email.read",
        "message.send",
        "message.read",
        "notification.create",
    ),
    "knowledge": ("search", "retrieve", "ingest", "summarize", "compare"),
    "reasoning": ("plan", "analyze", "compare", "explain", "decompose", "review"),
    "world_model": (
        "query",
        "update",
        "reconcile",
        "project",
        "timeline",
        "relationships",
        "snapshot",
    ),
    "system": ("status", "health", "logs", "settings", "update", "restart"),
    "llm": ("summarize", "rewrite", "extract", "classify"),
}


def build_v1_catalog() -> tuple[CapabilityDefinition, ...]:
    """Return full v1 catalog (wired + stubs)."""
    seen = {c.id for c in _WIRED}
    stubs: list[CapabilityDefinition] = []
    for domain, actions in _DOMAINS_STUB.items():
        for action in actions:
            cap_id = action if "." in action else f"{domain}.{action}"
            if cap_id in seen:
                continue
            seen.add(cap_id)
            stubs.append(
                CapabilityDefinition(
                    id=cap_id,
                    domain=domain if "." not in action else action.split(".", 1)[0],
                    description=f"{cap_id} (not yet wired)",
                    planner_visible=False,
                    execution_handler="Unimplemented",
                    tags=(domain, "stub"),
                )
            )
    # Alias launch_application → applications.launch for EA compatibility.
    aliases = (
        CapabilityDefinition(
            id="launch_application",
            domain="applications",
            description="Launch a desktop application (alias)",
            inputs=("application",),
            outputs=("status",),
            mutates_world_model=True,
            planner_visible=True,
            execution_handler="ApplicationLauncher",
            tags=("applications", "alias"),
        ),
    )
    return _WIRED + aliases + tuple(stubs)
