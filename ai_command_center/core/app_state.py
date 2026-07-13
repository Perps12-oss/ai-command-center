"""Central application state â€” updated only via event reducers."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from ai_command_center.core.event_bus import (
    EVENT_ACTION_REGISTERED,
    EVENT_RELATIONSHIP_CREATED,
    EVENT_TIMELINE_EVENT,
    Event,
    EventBus,
)
from ai_command_center.core.events.topics import (
    AGENT_SPAWNED,
    AGENT_TASK_COMPLETE,
    AGENT_TASK_REQUEST,
    AGENT_TERMINATED,
    AGENT_PIPELINE_COMPLETE,
    AGENT_PIPELINE_PLANNED,
    AGENT_PIPELINE_STAGE,
    AGENT_PIPELINE_STARTED,
    APP_ERROR,
    APP_PHASE,
    ARTIFACT_CREATED,
    ARTIFACT_UPDATED,
    ARTIFACTS_LOADED,
    PERMISSION_CHECK_REQUEST,
    PERMISSION_CHECK_RESULT,
    CHAT_CANCELLED,
    CHAT_CHUNK,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_HISTORY_LOADED,
    CHAT_STARTED,
    COMMAND_ROUTED,
    CONTEXT_SNAPSHOT_CREATED,
    ENTITY_CREATED,
    ENTITY_DELETED,
    ENTITY_RELATIONSHIPS_CHANGED,
    ENTITY_UPDATED,
    GOAL_ACTIVATED,
    GOAL_CANCELLED,
    GOAL_COMPLETED,
    GOAL_FAILED,
    GOAL_PAUSED,
    GOAL_RESUMED,
    GOAL_SUBMITTED,
    KERNEL_STATE_CHANGED,
    OBSERVATION_RECEIVED,
    MEMORY_CLEARED,
    MEMORY_SELECTED,
    MEMORY_STORED,
    MODEL_SELECTED,
    NOTE_CREATED,
    NOTE_INDEX_COMPLETE,
    NOTE_SEARCH_RESULTS,
    NOTE_SELECTED,
    NOTES_INDEXED,
    PLUGIN_CATALOG,
    PLUGIN_STATE_CHANGED,
    CAPABILITY_PROVIDERS_READY,
    CAPABILITY_LIFECYCLE_SNAPSHOT,
    CAPABILITY_CATALOG_RESULT,
    PLAN_GENERATED,
    RUNTIME_ACTION_COMPLETED,
    RUNTIME_ACTION_DENIED,
    RUNTIME_ACTION_FAILED,
    RUNTIME_ACTION_STARTED,
    RUNTIME_APPROVAL_REQUESTED,
    EXECUTION_RUN_STARTED,
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    EXECUTION_STEP_STARTED,
    EXECUTION_STEP_AWAITING_APPROVAL,
    EXECUTION_STEP_COMPLETED,
    EXECUTION_STEP_FAILED,
    ORCHESTRATION_PROVIDER_HEALTH,
    ORCHESTRATION_RUN_SNAPSHOT,
    EXECUTION_EVENT_APPENDED,
    EXECUTION_EVENTS_LOADED,
    EXECUTION_QUERY_RESULT,
    UI_EXECUTION_TIMELINE_SCRUB,
    UI_WORKFLOW_NODE_SELECT,
    UI_WORKFLOW_NODE_MOVE,
    UI_AUTOMATION_RUN,
    UI_AUTOMATION_SELECT,
    UI_AUTOMATION_SCHEDULE_TOGGLE,
    SERVICE_STATE_CHANGED,
    SETTINGS_CHANGED,
    SETTINGS_SNAPSHOT,
    SYSTEM_SNAPSHOT,
    JOURNAL_ENTRY_APPENDED,
    OPERATION_LOADED,
    OPERATION_SAVED,
    RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
    WORLD_MODEL_GRAPH_REFRESHED,
    WORLD_MODEL_MUTATION_APPLIED,
    WORLD_MODEL_NODE_DESELECTED,
    WORLD_MODEL_NODE_SELECTED,
    TOOL_COMPLETED,
    TOOL_FAILED,
    TOOL_STARTED,
    UI_INSPECT_CLEAR,
    UI_INSPECT_NAVIGATE,
    UI_INSPECT_SELECT,
    UI_OPEN_CHAT,
    UI_CHAT_NEW_SESSION,
    UI_SELECT_ENTITY,
    WORKSPACE_ACTIVE,
    WORKSPACE_DEACTIVATED,
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_RUNS_LOADED,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_STEP_STARTED,
)
from ai_command_center.domain.capability_lifecycle import CapabilityRecord
from ai_command_center.domain.capability_provider_settings import (
    capability_provider_map_from_payload,
)
from ai_command_center.platform.model_registry import normalize_tier_map
from ai_command_center.domain.provider_health_snapshot import ProviderHealthSnapshot
from ai_command_center.orchestration.state.orchestration_snapshot import OrchestrationRunSnapshot
from ai_command_center.core.state.artifact_state import ARTIFACT_REDUCERS, ArtifactCatalogItem
from ai_command_center.core.state.execution_event_state import (
    EXECUTION_EVENT_REDUCERS,
    ExecutionEventItem,
    ExecutionScrubberState,
)
from ai_command_center.core.state.model_state import ModelSelectionSnapshot
from ai_command_center.core.state.tool_state import ToolRunItem
from ai_command_center.core.state.execution_state import (
    ExecutionContext,
    SpanItem,
    reduce_execution_query_result,
)
from ai_command_center.core.state.execution_timeline_state import (
    ExecutionTimelineState,
    reduce_execution_timeline_state,
)
from ai_command_center.core.state.inspector_state import (
    InspectorState,
    reduce_inspector_state,
)
from ai_command_center.core.state.workflow_graph_state import (
    WorkflowGraphState,
    reduce_workflow_graph_state,
    seed_demo_workflow_graph,
)
from ai_command_center.core.projectors.automation_workspace_projector import (
    AutomationWorkspaceProjector,
)
from ai_command_center.core.state.automation_workspace_state import (
    reduce_automation_workspace_state,
)
from ai_command_center.domain.automation_workspace import AutomationWorkspaceState
from ai_command_center.domain.capability_library_snapshot import (
    CapabilityEntry,
    CapabilityLibrarySnapshot,
    ProviderEntry,
)
from ai_command_center.domain.agent_pipeline_snapshot import (
    AgentPipelineSnapshot,
    AgentRunSnapshot,
)
from ai_command_center.domain.provider_registry_snapshot import (
    ProviderEntry as ProviderRegistryEntry,
    ProviderRegistrySnapshot,
)
from ai_command_center.domain.permission_check_snapshot import (
    PendingCheck,
    PermissionCheckSnapshot,
    ResolvedCheck,
    _MAX_RESOLVED_HISTORY,
)
from ai_command_center.domain.workflow_library_snapshot import (
    WorkflowLibrarySnapshot,
    WorkflowRunSnapshot,
    WorkflowStepSnapshot,
    _MAX_WORKFLOW_HISTORY,
)
from ai_command_center.domain.execution_library_snapshot import (
    ExecutionLibrarySnapshot,
    ExecutionPlanSnapshot,
    ExecutionRunEntry,
    ExecutionStepSnapshot,
    _MAX_RUN_HISTORY,
)
from ai_command_center.domain.journal_entry import JournalEntry
from ai_command_center.domain.operation_snapshot import OperationSnapshot
from ai_command_center.domain.world_model_snapshot import (
    EdgeSnapshot,
    GoalSnapshot,
    MutationSnapshot,
    NodeSnapshot,
    WorldModelSnapshot,
    _attrs_to_pairs,
)
from ai_command_center.domain.settings_snapshot import SettingsSnapshot
from ai_command_center.domain.system_snapshot import SystemSnapshot

logger = logging.getLogger(__name__)

APP_STATE_TOPICS: tuple[str, ...] = (
    SERVICE_STATE_CHANGED,
    SETTINGS_CHANGED,
    SETTINGS_SNAPSHOT,
    COMMAND_ROUTED,
    CHAT_STARTED,
    CHAT_CHUNK,
    CHAT_COMPLETE,
    CHAT_CANCELLED,
    CHAT_ERROR,
    CHAT_HISTORY_LOADED,
    CONTEXT_SNAPSHOT_CREATED,
    APP_ERROR,
    APP_PHASE,
    SYSTEM_SNAPSHOT,
    # Notes / Memory / Plugins (Track 3.2)
    NOTE_SEARCH_RESULTS,
    NOTE_SELECTED,
    NOTE_CREATED,
    NOTE_INDEX_COMPLETE,
    NOTES_INDEXED,
    MEMORY_STORED,
    MEMORY_SELECTED,
    MEMORY_CLEARED,
    PLUGIN_CATALOG,
    PLUGIN_STATE_CHANGED,
    CAPABILITY_PROVIDERS_READY,
    CAPABILITY_LIFECYCLE_SNAPSHOT,
    CAPABILITY_CATALOG_RESULT,
    PLAN_GENERATED,
    KERNEL_STATE_CHANGED,
    GOAL_SUBMITTED,
    GOAL_ACTIVATED,
    GOAL_PAUSED,
    GOAL_RESUMED,
    GOAL_CANCELLED,
    GOAL_COMPLETED,
    GOAL_FAILED,
    OBSERVATION_RECEIVED,
    RUNTIME_ACTION_STARTED,
    RUNTIME_APPROVAL_REQUESTED,
    RUNTIME_ACTION_COMPLETED,
    RUNTIME_ACTION_FAILED,
    RUNTIME_ACTION_DENIED,
    # Workspace OS (Track B - Phase 2 + 3.2)
    ENTITY_CREATED,
    EVENT_RELATIONSHIP_CREATED,
    EVENT_ACTION_REGISTERED,
    EVENT_TIMELINE_EVENT,
    ENTITY_UPDATED,
    ENTITY_DELETED,
    ENTITY_RELATIONSHIPS_CHANGED,
    WORKSPACE_ACTIVE,
    WORKSPACE_DEACTIVATED,
    UI_OPEN_CHAT,
    UI_CHAT_NEW_SESSION,
    UI_INSPECT_SELECT,
    UI_INSPECT_CLEAR,
    UI_INSPECT_NAVIGATE,
    UI_SELECT_ENTITY,
    EXECUTION_EVENT_APPENDED,
    EXECUTION_EVENTS_LOADED,
    # Agent / workflow runs (Track R7)
    AGENT_SPAWNED,
    AGENT_TASK_REQUEST,
    AGENT_TASK_COMPLETE,
    AGENT_TERMINATED,
    AGENT_PIPELINE_STARTED,
    AGENT_PIPELINE_STAGE,
    AGENT_PIPELINE_PLANNED,
    AGENT_PIPELINE_COMPLETE,
    WORKFLOW_STARTED,
    WORKFLOW_STEP_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_RUNS_LOADED,
    PERMISSION_CHECK_REQUEST,
    PERMISSION_CHECK_RESULT,
    ORCHESTRATION_PROVIDER_HEALTH,
    ORCHESTRATION_RUN_SNAPSHOT,
    EXECUTION_QUERY_RESULT,
    MODEL_SELECTED,
    ARTIFACT_CREATED,
    ARTIFACT_UPDATED,
    ARTIFACTS_LOADED,
    UI_EXECUTION_TIMELINE_SCRUB,
    UI_WORKFLOW_NODE_SELECT,
    UI_WORKFLOW_NODE_MOVE,
    UI_AUTOMATION_RUN,
    UI_AUTOMATION_SELECT,
    UI_AUTOMATION_SCHEDULE_TOGGLE,
    EXECUTION_RUN_STARTED,
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    EXECUTION_STEP_STARTED,
    EXECUTION_STEP_AWAITING_APPROVAL,
    EXECUTION_STEP_COMPLETED,
    EXECUTION_STEP_FAILED,
    JOURNAL_ENTRY_APPENDED,
    OPERATION_LOADED,
    OPERATION_SAVED,
    RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
    WORLD_MODEL_GRAPH_REFRESHED,
    WORLD_MODEL_MUTATION_APPLIED,
    WORLD_MODEL_NODE_DESELECTED,
    WORLD_MODEL_NODE_SELECTED,
    TOOL_COMPLETED,
    TOOL_FAILED,
    TOOL_STARTED,
)


@dataclass(frozen=True, slots=True)
class ServiceSnapshot:
    name: str
    state: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class WorkspaceOsEntity:
    """Lightweight Workspace OS entity projection."""

    entity_id: str = ""
    entity_type: str = ""
    title: str = ""
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class WorkspaceOsSnapshot:
    """Workspace OS projection for the inspector UI."""

    entity_count: int = 0
    relationship_count: int = 0
    action_count: int = 0
    event_count: int = 0
    recent_events: tuple[str, ...] = ()
    entities: tuple[WorkspaceOsEntity, ...] = ()


@dataclass(frozen=True, slots=True)
class NoteItem:
    """Projection of a note search result."""

    path: str = ""
    title: str = ""
    snippet: str = ""


@dataclass(frozen=True, slots=True)
class MemoryItem:
    """Projection of a stored memory node."""

    node_id: str = ""
    label: str = ""
    workspace_id: str = ""
    entity_id: str = ""


def _memory_catalog_for_workspace(
    catalog: tuple[MemoryItem, ...],
    workspace_id: str,
) -> tuple[MemoryItem, ...]:
    """Keep catalog entries visible for the active workspace scope."""
    if not workspace_id:
        return catalog
    return tuple(
        item
        for item in catalog
        if not item.workspace_id or item.workspace_id == workspace_id
    )


@dataclass(frozen=True, slots=True)
class ChatHistoryMessage:
    """Projection of a persisted chat message."""

    role: str = ""
    content: str = ""


@dataclass(frozen=True, slots=True)
class PluginItem:
    """Projection of a plugin catalog entry."""

    plugin_id: str = ""
    name: str = ""
    description: str = ""
    kind: str = "extension"
    enabled: bool = True
    error: str = ""
    pending_restart: bool = False


@dataclass(frozen=True, slots=True)
class RuntimeProviderItem:
    """Projection of a discovered runtime provider."""

    provider_id: str = ""
    name: str = ""
    version: str = ""
    capabilities: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    health_state: str = ""
    health_detail: str = ""
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class ExecutionRunItem:
    """Lightweight execution run feed entry."""

    run_id: str = ""
    request_id: str = ""
    source: str = ""
    created_at: float = 0.0
    summary: str = ""


@dataclass(frozen=True, slots=True)
class AgentRunItem:
    """Projection of an agent run for UI rendering."""

    agent_id: str = ""
    request_id: str = ""
    state: str = "spawning"
    task: str = ""
    error: str = ""
    steps: int = 0
    workspace_id: str = ""
    workspace_entity_id: str = ""
    spawn_role: str = ""


@dataclass(frozen=True, slots=True)
class PermissionCheckItem:
    """Pending interactive permission check surfaced to the UI."""

    check_id: str = ""
    permissions: tuple[str, ...] = ()
    actor_type: str = "agent"
    actor_id: str = ""
    summary: str = ""
    interactive: bool = False


@dataclass(frozen=True, slots=True)
class WorkflowRunItem:
    """Projection of a workflow run for UI rendering."""

    run_id: str = ""
    workflow_id: str = ""
    state: str = "pending"
    current_step_id: str = ""
    current_step_index: int = 0
    total_steps: int = 0
    error: str = ""


_MAX_RUN_FEED = 20
@dataclass(frozen=True, slots=True)
class AppState:
    """Immutable snapshot of application state."""

    phase: str = "idle"
    services: tuple[ServiceSnapshot, ...] = ()
    settings: SettingsSnapshot = field(default_factory=SettingsSnapshot)
    system_snapshot: SystemSnapshot = field(default_factory=SystemSnapshot)
    workspace_os: WorkspaceOsSnapshot = field(default_factory=WorkspaceOsSnapshot)
    last_event_topic: str = ""
    last_event_source: str = ""
    settings_version: int = 0
    last_command: str = ""
    last_command_intent: str = ""
    active_chat_request_id: str = ""
    last_chat_request_id: str = ""
    chat_status: str = "idle"
    chat_streaming: bool = False
    chat_stream_buffer: str = ""
    chat_stream_revision: int = 0
    chat_pending_user_text: str = ""
    chat_started_user_text: str = ""
    chat_context_sources: tuple[str, ...] = ()
    chat_token_estimate: int = 0
    workspace_context_snippet_count: int = 0
    last_workspace_context_workspace_id: str = ""
    last_assistant_message: str = ""
    chat_history_count: int = 0
    chat_history_messages: tuple[ChatHistoryMessage, ...] = ()
    chat_history_revision: int = 0
    last_chat_error: str = ""
    chat_workspace_entity_id: str = ""
    chat_workspace_entity_type: str = ""
    chat_workspace_entity_title: str = ""
    chat_workspace_entity_description: str = ""
    chat_workspace_entity_url: str = ""
    chat_workspace_entity_path: str = ""
    active_workspace_id: str = ""
    active_workspace_title: str = ""
    selected_entity_id: str = ""
    selected_entity_type: str = ""
    selected_entity_title: str = ""
    chat_active_session_key: str = "default"
    errors: tuple[str, ...] = ()

    # Track 3.2 â€” full projection of feature catalogs
    notes_catalog: tuple[NoteItem, ...] = ()
    note_selected: NoteItem | None = None
    note_index_status: tuple[int, int] = ()  # (files, ms)
    memory_catalog: tuple[MemoryItem, ...] = ()
    memory_selected: tuple[str, ...] = ()
    plugin_catalog: tuple[PluginItem, ...] = ()

    # Track R7 â€” agent / workflow run projections
    agent_runs: tuple[AgentRunItem, ...] = ()
    workflow_runs: tuple[WorkflowRunItem, ...] = ()
    active_agent_run_id: str = ""
    active_agent_run_ids: tuple[str, ...] = ()
    active_agent_pipeline_id: str = ""
    agent_pipeline_stage: str = ""
    agent_pipeline_planned_tools: tuple[str, ...] = ()
    # Blueprint Phase 5 — Agent Pipeline AppState projection
    agent_pipeline: AgentPipelineSnapshot = field(
        default_factory=AgentPipelineSnapshot
    )
    active_workflow_run_id: str = ""
    # Blueprint Phase 7 — Workflow Library AppState projection
    workflow_library: WorkflowLibrarySnapshot = field(
        default_factory=WorkflowLibrarySnapshot
    )
    pending_permission_check: PermissionCheckItem | None = None
    permission_check_revision: int = 0
    # Blueprint Phase 8 — Permission Check AppState projection
    permission_snapshot: PermissionCheckSnapshot = field(
        default_factory=PermissionCheckSnapshot
    )
    orchestration_run: OrchestrationRunSnapshot = field(default_factory=OrchestrationRunSnapshot)
    provider_health_map: tuple[ProviderHealthSnapshot, ...] = ()
    runtime_capability_providers: tuple[RuntimeProviderItem, ...] = ()
    # Blueprint Phase 6 — Provider Registry AppState projection
    provider_registry: ProviderRegistrySnapshot = field(
        default_factory=ProviderRegistrySnapshot
    )
    capability_lifecycle: tuple[CapabilityRecord, ...] = ()
    capability_prompt_catalog: tuple[dict[str, object], ...] = ()
    capability_library: CapabilityLibrarySnapshot = field(
        default_factory=CapabilityLibrarySnapshot
    )
    planner_last_plan: dict[str, object] = field(default_factory=dict)
    execution_active_plan: dict[str, object] = field(default_factory=dict)
    execution_current_step: dict[str, object] = field(default_factory=dict)
    execution_runs: tuple[ExecutionRunItem, ...] = ()
    # Blueprint Phase 4 — Execution Library AppState projection
    execution_library: ExecutionLibrarySnapshot = field(
        default_factory=ExecutionLibrarySnapshot
    )
    execution_context: ExecutionContext = field(default_factory=ExecutionContext)
    execution_scrubber: ExecutionScrubberState = field(default_factory=ExecutionScrubberState)
    inspector: InspectorState = field(default_factory=InspectorState)
    model_selection: ModelSelectionSnapshot = field(default_factory=ModelSelectionSnapshot)
    recent_tool_runs: tuple[ToolRunItem, ...] = ()
    recent_artifacts: tuple[ArtifactCatalogItem, ...] = ()
    recent_execution_events: tuple[ExecutionEventItem, ...] = ()
    execution_timeline: ExecutionTimelineState = field(default_factory=ExecutionTimelineState)
    workflow_graph: WorkflowGraphState = field(default_factory=seed_demo_workflow_graph)
    automation_workspace: AutomationWorkspaceState = field(
        default_factory=lambda: AutomationWorkspaceProjector.project_state(())
    )
    brain_kernel_state: str = "boot"
    brain_recent_goals: tuple[dict[str, object], ...] = ()
    brain_recent_observations: tuple[dict[str, object], ...] = ()
    brain_recent_runtime_actions: tuple[dict[str, object], ...] = ()

    # Blueprint Phase 1 — Operations Library & Journal
    operation_library_index: tuple[OperationSnapshot, ...] = ()
    operation_journal: tuple[JournalEntry, ...] = ()
    active_operation: OperationSnapshot | None = None
    journal_entry_counter: int = 0

    # Blueprint Phase 2 — World Model AppState projection
    world_model: WorldModelSnapshot = field(default_factory=WorldModelSnapshot)
Reducer = Callable[[AppState, Event], AppState]


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return default


def _coerce_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def _coerce_float(value: Any, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _settings_from_payload(payload: dict[str, Any]) -> SettingsSnapshot:
    return SettingsSnapshot(
        theme=str(payload.get("theme", "dark")),
        accent=str(payload.get("accent", "#3B82F6")),
        default_model=str(payload.get("default_model", "llama3.2:3b")),
        summarize_model=str(payload.get("summarize_model", "llama3.2:3b")),
        model_tier_map=normalize_tier_map(
            payload.get("model_tier_map"),
            default_model=str(payload.get("default_model", "llama3.2:3b")),
        ),
        ollama_url=str(payload.get("ollama_url", "http://localhost:11434")),
        hotkey=str(payload.get("hotkey", "alt+space")),
        low_memory_mode=_coerce_bool(payload.get("low_memory_mode", False)),
        window_width=_coerce_int(payload.get("window_width", 1100), 1100),
        window_height=_coerce_int(payload.get("window_height", 700), 700),
        window_alpha=_coerce_float(payload.get("window_alpha", 0.95), 0.95),
        obsidian_vault_path=str(payload.get("obsidian_vault_path", "")),
        overlay_mode=str(payload.get("overlay_mode", "palette")),
        model_name=str(payload.get("model_name", "llama3.2:3b")),
        provider=str(payload.get("provider", "ollama")),
        openai_base_url=str(payload.get("openai_base_url", "https://api.openai.com/v1")),
        openai_api_key=str(payload.get("openai_api_key", "")),
        vault_path=str(payload.get("vault_path", "")),
        overlay_hotkey=str(payload.get("overlay_hotkey", "alt+space")),
        telemetry_enabled=_coerce_bool(payload.get("telemetry_enabled", True)),
        otel_enabled=_coerce_bool(payload.get("otel_enabled", False)),
        otel_endpoint=str(payload.get("otel_endpoint", "http://127.0.0.1:4318")),
        schema_version=_coerce_int(payload.get("schema_version", 1), 1),
        capability_provider_map=capability_provider_map_from_payload(payload),
        qwenpaw_enabled=_coerce_bool(payload.get("qwenpaw_enabled", False)),
        qwenpaw_url=str(payload.get("qwenpaw_url", "http://127.0.0.1:8088")),
        qwenpaw_agent_id=str(payload.get("qwenpaw_agent_id", "default")),
        qwenpaw_auto_start=_coerce_bool(payload.get("qwenpaw_auto_start", False)),
        qwenpaw_python=str(payload.get("qwenpaw_python", "")),
        qwenpaw_auth_token=str(payload.get("qwenpaw_auth_token", "")),
    )


def _reduce_service_state(state: AppState, event: Event) -> AppState:
    if event.topic != SERVICE_STATE_CHANGED:
        return state
    name = str(event.payload.get("name", ""))
    new_state = str(event.payload.get("state", "off"))
    detail = str(event.payload.get("detail", ""))
    updated = {s.name: s for s in state.services}
    updated[name] = ServiceSnapshot(name=name, state=new_state, detail=detail)
    services = tuple(sorted(updated.values(), key=lambda s: s.name))
    return replace(
        state,
        services=services,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_settings_changed(state: AppState, event: Event) -> AppState:
    if event.topic != SETTINGS_CHANGED:
        return state
    return replace(
        state,
        settings_version=state.settings_version + 1,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_settings_snapshot(state: AppState, event: Event) -> AppState:
    if event.topic != SETTINGS_SNAPSHOT:
        return state
    return replace(
        state,
        settings=_settings_from_payload(event.payload),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_error(state: AppState, event: Event) -> AppState:
    if event.topic != APP_ERROR:
        return state
    message = str(event.payload.get("message", "unknown error"))
    errors = state.errors + (message,)
    if len(errors) > 20:
        errors = errors[-20:]
    return replace(
        state,
        errors=errors,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_phase(state: AppState, event: Event) -> AppState:
    if event.topic != APP_PHASE:
        return state
    phase = str(event.payload.get("phase", state.phase))
    return replace(
        state,
        phase=phase,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


_METRICS_ONLY_EXTRA_KEYS = frozenset(
    {
        "eventbus_topic_counts",
        "cpu_delta",
        "ram_delta",
        "model_load",
        "network",
        "health",
    }
)


def system_snapshot_metrics_only_delta(
    old: SystemSnapshot,
    new: SystemSnapshot,
) -> bool:
    """Return True when only polling metrics drifted (no UI-structural change)."""
    if old.phase != new.phase:
        return False
    if old.ollama_online != new.ollama_online:
        return False
    if old.service_states != new.service_states:
        return False
    if old.tool_count != new.tool_count:
        return False
    if old.recent_commands != new.recent_commands:
        return False
    old_extra = dict(old.extra)
    new_extra = dict(new.extra)
    if old_extra.get("openai_online") != new_extra.get("openai_online"):
        return False
    structural_keys = (set(old_extra) | set(new_extra)) - _METRICS_ONLY_EXTRA_KEYS
    for key in structural_keys:
        if old_extra.get(key) != new_extra.get(key):
            return False
    return True


def _reduce_system_snapshot(state: AppState, event: Event) -> AppState:
    if event.topic != SYSTEM_SNAPSHOT:
        return state
    payload = dict(event.payload)
    snapshot = SystemSnapshot(
        phase=str(payload.get("phase", state.system_snapshot.phase)),
        cpu_percent=float(payload.get("cpu_percent", state.system_snapshot.cpu_percent)),
        ram_percent=float(payload.get("ram_percent", state.system_snapshot.ram_percent)),
        ollama_online=bool(payload.get("ollama_online", state.system_snapshot.ollama_online)),
        service_states=tuple(payload.get("service_states", state.system_snapshot.service_states)),
        tool_count=int(payload.get("tool_count", state.system_snapshot.tool_count)),
        recent_commands=tuple(payload.get("recent_commands", state.system_snapshot.recent_commands)),
        event_rate=float(payload.get("event_rate", state.system_snapshot.event_rate)),
        uptime=float(payload.get("uptime", state.system_snapshot.uptime)),
        extra=dict(payload.get("extra", state.system_snapshot.extra)),
    )
    return replace(
        state,
        system_snapshot=snapshot,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_note_results(state: AppState, event: Event) -> AppState:
    """Project note search results into AppState."""
    if event.topic != NOTE_SEARCH_RESULTS:
        return state
    raw_results = event.payload.get("results") or []
    items: list[NoteItem] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        items.append(
            NoteItem(
                path=str(item.get("path", "")),
                title=str(item.get("title", "")),
                snippet=str(item.get("snippet", "")),
            )
        )
    return replace(
        state,
        notes_catalog=tuple(items),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_note_selected(state: AppState, event: Event) -> AppState:
    """Project selected note preview into AppState."""
    if event.topic != NOTE_SELECTED:
        return state
    selected = NoteItem(
        path=str(event.payload.get("path", "")),
        title=str(event.payload.get("title", "")),
        snippet=str(event.payload.get("body", "")),
    )
    return replace(
        state,
        note_selected=selected,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_note_created(state: AppState, event: Event) -> AppState:
    """Append newly created note to the catalog."""
    if event.topic != NOTE_CREATED:
        return state
    path = str(event.payload.get("path", ""))
    item = NoteItem(path=path, title=path, snippet="")
    return replace(
        state,
        notes_catalog=(item,) + state.notes_catalog,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_note_index_complete(state: AppState, event: Event) -> AppState:
    """Record note indexing status."""
    if event.topic != NOTE_INDEX_COMPLETE:
        return state
    files = int(event.payload.get("indexed_files", event.payload.get("files", 0)))
    ms = int(event.payload.get("index_ms", event.payload.get("ms", 0)))
    return replace(
        state,
        note_index_status=(files, ms),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_memory_stored(state: AppState, event: Event) -> AppState:
    """Append newly stored memory to the catalog."""
    if event.topic != MEMORY_STORED:
        return state
    workspace_id = str(event.payload.get("workspace_id", ""))
    entity_id = str(event.payload.get("entity_id", ""))
    active = state.active_workspace_id
    if active and workspace_id and workspace_id != active:
        return replace(
            state,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )
    item = MemoryItem(
        node_id=str(event.payload.get("id", "")),
        label=str(event.payload.get("label", "")),
        workspace_id=workspace_id,
        entity_id=entity_id,
    )
    catalog = _memory_catalog_for_workspace((item,) + state.memory_catalog, active)
    return replace(
        state,
        memory_catalog=catalog,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_workspace_memory_catalog(state: AppState, event: Event) -> AppState:
    """Filter memory catalog when active workspace scope changes."""
    if event.topic == WORKSPACE_ACTIVE:
        workspace_id = str(event.payload.get("workspace_id", "")).strip()
        return replace(
            state,
            memory_catalog=_memory_catalog_for_workspace(state.memory_catalog, workspace_id),
            last_event_topic=event.topic,
            last_event_source=event.source,
        )
    if event.topic == WORKSPACE_DEACTIVATED:
        cleared_id = str(event.payload.get("workspace_id", "")).strip()
        if cleared_id and cleared_id != state.active_workspace_id:
            return state
        return replace(
            state,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )
    return state


def _reduce_memory_selected(state: AppState, event: Event) -> AppState:
    """Project selected memory labels into AppState."""
    if event.topic != MEMORY_SELECTED:
        return state
    labels = event.payload.get("labels")
    if isinstance(labels, (list, tuple)):
        selected = tuple(str(label) for label in labels)
    else:
        selected = ()
    return replace(
        state,
        memory_selected=selected,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_memory_cleared(state: AppState, event: Event) -> AppState:
    """Handle memory selection clear or node deletion."""
    if event.topic != MEMORY_CLEARED:
        return state
    node_id = str(event.payload.get("id", ""))
    if node_id:
        catalog = tuple(item for item in state.memory_catalog if item.node_id != node_id)
        return replace(
            state,
            memory_catalog=catalog,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )
    return replace(
        state,
        memory_selected=(),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_plugin_catalog(state: AppState, event: Event) -> AppState:
    """Project plugin catalog into AppState."""
    if event.topic != PLUGIN_CATALOG:
        return state
    raw_plugins = event.payload.get("plugins") or []
    items: list[PluginItem] = []
    for plugin in raw_plugins:
        if not isinstance(plugin, dict):
            continue
        items.append(
            PluginItem(
                plugin_id=str(plugin.get("id", "")),
                name=str(plugin.get("name", "")),
                description=str(plugin.get("description", "")),
                kind=str(plugin.get("kind", "extension")),
                enabled=bool(plugin.get("enabled", True)),
                error=str(plugin.get("error", "")),
                pending_restart=bool(plugin.get("pending_restart", False)),
            )
        )
    return replace(
        state,
        plugin_catalog=tuple(items),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_capability_providers_ready(state: AppState, event: Event) -> AppState:
    """Record capability.providers.ready and merge runtime provider health."""
    if event.topic != CAPABILITY_PROVIDERS_READY:
        return state
    providers = event.payload.get("providers") or []
    runtime_items: list[RuntimeProviderItem] = []
    health_items: dict[str, ProviderHealthSnapshot] = {
        h.provider_id: h for h in state.provider_health_map
    }
    for item in providers:
        if not isinstance(item, dict):
            continue
        provider_id = str(item.get("id", ""))
        runtime_items.append(
            RuntimeProviderItem(
                provider_id=provider_id,
                name=str(item.get("name", provider_id)),
                version=str(item.get("version", "")),
                capabilities=tuple(str(c) for c in (item.get("capabilities") or [])),
                permissions=tuple(str(p) for p in (item.get("permissions") or [])),
                health_state=str(item.get("health_state", "")),
                health_detail=str(item.get("health_detail", "")),
                enabled=bool(item.get("enabled", True)),
            )
        )
        snap = ProviderHealthSnapshot.from_runtime_payload(item)
        health_items[snap.provider_id] = snap
    return replace(
        state,
        runtime_capability_providers=tuple(runtime_items),
        provider_health_map=tuple(health_items.values()),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_orchestration_provider_health(state: AppState, event: Event) -> AppState:
    if event.topic != ORCHESTRATION_PROVIDER_HEALTH:
        return state
    snap = ProviderHealthSnapshot.from_orchestration_payload(event.payload)
    health_items: dict[str, ProviderHealthSnapshot] = {
        h.provider_id: h for h in state.provider_health_map
    }
    health_items[snap.provider_id] = snap
    return replace(
        state,
        provider_health_map=tuple(health_items.values()),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_capability_lifecycle_snapshot(state: AppState, event: Event) -> AppState:
    if event.topic != CAPABILITY_LIFECYCLE_SNAPSHOT:
        return state
    raw_records = event.payload.get("capability_lifecycle") or []
    records: list[CapabilityRecord] = []
    for item in raw_records:
        if not isinstance(item, dict):
            continue
        records.append(CapabilityRecord.from_dict(item))
    return replace(
        state,
        capability_lifecycle=tuple(records),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_capability_prompt_catalog(state: AppState, event: Event) -> AppState:
    if event.topic != CAPABILITY_CATALOG_RESULT:
        return state
    raw_specs = event.payload.get("specs") or []
    specs: list[dict[str, object]] = []
    for item in raw_specs:
        if isinstance(item, dict):
            specs.append(dict(item))
    return replace(
        state,
        capability_prompt_catalog=tuple(specs),
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_planner_last_plan(state: AppState, event: Event) -> AppState:
    if event.topic != PLAN_GENERATED:
        return state
    raw_plan = event.payload.get("plan")
    plan_dict: dict[str, object] = {}
    if isinstance(raw_plan, dict):
        plan_dict = dict(raw_plan)
    return replace(
        state,
        planner_last_plan=plan_dict,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_execution_orchestrator(state: AppState, event: Event) -> AppState:
    topic = event.topic
    payload = event.payload
    if topic == EXECUTION_RUN_STARTED:
        plan_dict: dict[str, object] = {
            "run_id": str(payload.get("run_id", "")),
            "request_id": str(payload.get("request_id", "")),
            "goal": str(payload.get("goal", "")),
            "total_steps": payload.get("total_steps", 0),
            "steps": list(payload.get("steps") or []),
            "status": "running",
        }
        return replace(
            state,
            execution_active_plan=plan_dict,
            execution_current_step={},
            last_event_topic=topic,
            last_event_source=event.source,
        )
    if topic in {EXECUTION_STEP_STARTED, EXECUTION_STEP_AWAITING_APPROVAL}:
        step_dict: dict[str, object] = {
            "run_id": str(payload.get("run_id", "")),
            "step_id": str(payload.get("step_id", "")),
            "index": payload.get("index", 0),
            "capability": str(payload.get("capability", "")),
            "risk": str(payload.get("risk", "")),
            "status": "awaiting_approval"
            if topic == EXECUTION_STEP_AWAITING_APPROVAL
            else "started",
        }
        active = dict(state.execution_active_plan)
        if active:
            active["current_step_id"] = step_dict["step_id"]
        return replace(
            state,
            execution_active_plan=active,
            execution_current_step=step_dict,
            last_event_topic=topic,
            last_event_source=event.source,
        )
    if topic == EXECUTION_STEP_COMPLETED:
        active = dict(state.execution_active_plan)
        if active:
            raw_steps = active.get("steps")
            if isinstance(raw_steps, list):
                step_id = str(payload.get("step_id", ""))
                updated_steps: list[object] = []
                for item in raw_steps:
                    if isinstance(item, dict) and str(item.get("step_id")) == step_id:
                        merged = dict(item)
                        merged["status"] = "completed"
                        updated_steps.append(merged)
                    else:
                        updated_steps.append(item)
                active["steps"] = updated_steps
        return replace(
            state,
            execution_active_plan=active,
            last_event_topic=topic,
            last_event_source=event.source,
        )
    if topic in {EXECUTION_RUN_COMPLETE, EXECUTION_RUN_FAILED}:
        active = dict(state.execution_active_plan)
        if active:
            active["status"] = "complete" if topic == EXECUTION_RUN_COMPLETE else "failed"
            if topic == EXECUTION_RUN_FAILED:
                active["error"] = str(payload.get("error", ""))
        return replace(
            state,
            execution_active_plan=active,
            execution_current_step={}
            if topic == EXECUTION_RUN_COMPLETE
            else state.execution_current_step,
            last_event_topic=topic,
            last_event_source=event.source,
        )
    if topic == EXECUTION_STEP_FAILED:
        step_dict = dict(state.execution_current_step)
        step_dict["status"] = "failed"
        step_dict["error"] = str(payload.get("error", ""))
        active = dict(state.execution_active_plan)
        if active:
            active["status"] = "failed"
            active["error"] = str(payload.get("error", ""))
        return replace(
            state,
            execution_active_plan=active,
            execution_current_step=step_dict,
            last_event_topic=topic,
            last_event_source=event.source,
        )
    return state


def _reduce_execution_run_feed(state: AppState, event: Event) -> AppState:
    if event.topic not in {ORCHESTRATION_RUN_SNAPSHOT, CHAT_COMPLETE}:
        return state
    payload = event.payload
    request_id = str(payload.get("request_id", "")).strip()
    if not request_id:
        return state
    if event.topic == CHAT_COMPLETE and payload.get("orchestration"):
        return state
    source = "orchestration" if event.topic == ORCHESTRATION_RUN_SNAPSHOT else "chat"
    summary = str(payload.get("intent", payload.get("text", "")))[:120]
    item = ExecutionRunItem(
        run_id=f"{request_id}:{source}:{len(state.execution_runs)}",
        request_id=request_id,
        source=source,
        created_at=0.0,
        summary=summary,
    )
    runs = state.execution_runs + (item,)
    if len(runs) > 50:
        runs = runs[-50:]
    return replace(
        state,
        execution_runs=runs,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_plugin_state_changed(state: AppState, event: Event) -> AppState:
    """Update enabled flag for a plugin in the catalog."""
    if event.topic != PLUGIN_STATE_CHANGED:
        return state
    plugin_id = str(event.payload.get("id", ""))
    enabled = bool(event.payload.get("enabled", True))
    updated = tuple(
        replace(item, enabled=enabled) if item.plugin_id == plugin_id else item
        for item in state.plugin_catalog
    )
    return replace(
        state,
        plugin_catalog=updated,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _find_agent_run(runs: tuple[AgentRunItem, ...], agent_id: str) -> AgentRunItem | None:
    for run in runs:
        if run.agent_id == agent_id:
            return run
    return None


def _upsert_agent_run(runs: tuple[AgentRunItem, ...], item: AgentRunItem) -> tuple[AgentRunItem, ...]:
    filtered = tuple(r for r in runs if r.agent_id != item.agent_id)
    updated = (item,) + filtered
    if len(updated) > _MAX_RUN_FEED:
        updated = updated[:_MAX_RUN_FEED]
    return updated


def _find_workflow_run(runs: tuple[WorkflowRunItem, ...], run_id: str) -> WorkflowRunItem | None:
    for run in runs:
        if run.run_id == run_id:
            return run
    return None


def _upsert_workflow_run(
    runs: tuple[WorkflowRunItem, ...], item: WorkflowRunItem
) -> tuple[WorkflowRunItem, ...]:
    filtered = tuple(r for r in runs if r.run_id != item.run_id)
    updated = (item,) + filtered
    if len(updated) > _MAX_RUN_FEED:
        updated = updated[:_MAX_RUN_FEED]
    return updated


def _add_active_agent_id(active_ids: tuple[str, ...], agent_id: str) -> tuple[str, ...]:
    if not agent_id or agent_id in active_ids:
        return active_ids
    return (agent_id,) + active_ids


def _remove_active_agent_id(active_ids: tuple[str, ...], agent_id: str) -> tuple[str, ...]:
    return tuple(item for item in active_ids if item != agent_id)


def _reduce_agent_run(state: AppState, event: Event) -> AppState:
    """Project agent lifecycle events into agent_runs feed."""
    if event.topic not in {
        AGENT_SPAWNED,
        AGENT_TASK_REQUEST,
        AGENT_TASK_COMPLETE,
        AGENT_TERMINATED,
    }:
        return state

    payload = event.payload
    agent_id = str(payload.get("agent_id", ""))
    if not agent_id:
        return state

    existing = _find_agent_run(state.agent_runs, agent_id)
    request_id = str(payload.get("request_id") or (existing.request_id if existing else ""))
    task = str(payload.get("task") or (existing.task if existing else ""))
    steps = _coerce_int(payload.get("steps"), existing.steps if existing else 0)
    workspace_id = str(
        payload.get("workspace_id") or (existing.workspace_id if existing else "")
    )
    workspace_entity_id = str(
        payload.get("workspace_entity_id")
        or (existing.workspace_entity_id if existing else "")
    )
    spawn_role = str(payload.get("spawn_role") or (existing.spawn_role if existing else ""))
    if event.topic == AGENT_TERMINATED:
        error = str(payload.get("error", ""))
    else:
        error = str(payload.get("error") or (existing.error if existing else ""))

    if event.topic == AGENT_SPAWNED:
        run_state = str(payload.get("state", "spawning"))
        item = AgentRunItem(
            agent_id=agent_id,
            request_id=request_id,
            state=run_state,
            task=task,
            workspace_id=workspace_id,
            workspace_entity_id=workspace_entity_id,
            spawn_role=spawn_role,
        )
        active_ids = _add_active_agent_id(state.active_agent_run_ids, agent_id)
        return replace(
            state,
            agent_runs=_upsert_agent_run(state.agent_runs, item),
            active_agent_run_id=agent_id,
            active_agent_run_ids=active_ids,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )

    if existing is None:
        existing = AgentRunItem(agent_id=agent_id, request_id=request_id)

    if event.topic == AGENT_TASK_REQUEST:
        run_state = "running"
        steps = existing.steps + 1
    elif event.topic == AGENT_TASK_COMPLETE:
        run_state = "waiting"
    elif event.topic == AGENT_TERMINATED:
        run_state = "failed" if error else "terminated"
    else:
        run_state = existing.state

    item = AgentRunItem(
        agent_id=agent_id,
        request_id=request_id,
        state=run_state,
        task=task or existing.task,
        error=error,
        steps=steps if steps else existing.steps,
        workspace_id=workspace_id or existing.workspace_id,
        workspace_entity_id=workspace_entity_id or existing.workspace_entity_id,
        spawn_role=spawn_role or existing.spawn_role,
    )
    active_id = state.active_agent_run_id
    active_ids = state.active_agent_run_ids
    if event.topic == AGENT_TERMINATED:
        active_ids = _remove_active_agent_id(active_ids, agent_id)
        if active_id == agent_id:
            active_id = active_ids[0] if active_ids else ""

    return replace(
        state,
        agent_runs=_upsert_agent_run(state.agent_runs, item),
        active_agent_run_id=active_id,
        active_agent_run_ids=active_ids,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_agent_pipeline(state: AppState, event: Event) -> AppState:
    """Project agent pipeline orchestration events (Track 7 A4)."""
    if event.topic not in {
        AGENT_PIPELINE_STARTED,
        AGENT_PIPELINE_STAGE,
        AGENT_PIPELINE_PLANNED,
        AGENT_PIPELINE_COMPLETE,
    }:
        return state

    payload = event.payload
    pipeline_id = str(payload.get("pipeline_id", ""))
    stage = str(payload.get("stage", ""))
    planned_raw = payload.get("planned_tools") or ()
    planned_tools = tuple(str(item) for item in planned_raw) if planned_raw else ()

    if event.topic == AGENT_PIPELINE_STARTED:
        return replace(
            state,
            active_agent_pipeline_id=pipeline_id,
            agent_pipeline_stage=stage or "starting",
            agent_pipeline_planned_tools=planned_tools,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )

    if event.topic == AGENT_PIPELINE_PLANNED:
        return replace(
            state,
            agent_pipeline_planned_tools=planned_tools or state.agent_pipeline_planned_tools,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )

    if event.topic == AGENT_PIPELINE_STAGE:
        return replace(
            state,
            active_agent_pipeline_id=pipeline_id or state.active_agent_pipeline_id,
            agent_pipeline_stage=stage,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )

    if event.topic == AGENT_PIPELINE_COMPLETE:
        return replace(
            state,
            active_agent_pipeline_id="",
            agent_pipeline_stage="complete",
            agent_pipeline_planned_tools=(),
            last_event_topic=event.topic,
            last_event_source=event.source,
        )

    return state


def _reduce_workflow_run(state: AppState, event: Event) -> AppState:
    """Project workflow lifecycle events into workflow_runs feed."""
    if event.topic not in {
        WORKFLOW_STARTED,
        WORKFLOW_STEP_STARTED,
        WORKFLOW_STEP_COMPLETED,
        WORKFLOW_COMPLETED,
        WORKFLOW_FAILED,
    }:
        return state

    payload = event.payload
    run_id = str(payload.get("run_id", ""))
    if not run_id:
        return state

    existing = _find_workflow_run(state.workflow_runs, run_id)
    workflow_id = str(
        payload.get("workflow_id") or (existing.workflow_id if existing else "")
    )
    total_steps = _coerce_int(
        payload.get("total_steps"),
        existing.total_steps if existing else 0,
    )
    step_id = str(payload.get("step_id") or (existing.current_step_id if existing else ""))
    step_index = _coerce_int(
        payload.get("index"),
        existing.current_step_index if existing else 0,
    )
    if event.topic == WORKFLOW_COMPLETED:
        error = str(payload.get("error", ""))
    elif event.topic == WORKFLOW_FAILED:
        error = str(payload.get("error") or (existing.error if existing else ""))
    else:
        error = str(payload.get("error") or (existing.error if existing else ""))

    if event.topic == WORKFLOW_STARTED:
        item = WorkflowRunItem(
            run_id=run_id,
            workflow_id=workflow_id,
            state="running",
            total_steps=total_steps,
        )
        return replace(
            state,
            workflow_runs=_upsert_workflow_run(state.workflow_runs, item),
            active_workflow_run_id=run_id,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )

    if existing is None:
        existing = WorkflowRunItem(run_id=run_id, workflow_id=workflow_id, state="running")

    if event.topic == WORKFLOW_STEP_STARTED:
        run_state = "running"
    elif event.topic == WORKFLOW_STEP_COMPLETED:
        run_state = "running"
        step_index = step_index + 1
    elif event.topic == WORKFLOW_COMPLETED:
        run_state = "completed"
    elif event.topic == WORKFLOW_FAILED:
        run_state = "failed"
    else:
        run_state = existing.state

    item = WorkflowRunItem(
        run_id=run_id,
        workflow_id=workflow_id or existing.workflow_id,
        state=run_state,
        current_step_id=step_id or existing.current_step_id,
        current_step_index=step_index,
        total_steps=total_steps or existing.total_steps,
        error=error,
    )
    active_id = state.active_workflow_run_id
    if event.topic in {WORKFLOW_COMPLETED, WORKFLOW_FAILED} and active_id == run_id:
        active_id = ""

    return replace(
        state,
        workflow_runs=_upsert_workflow_run(state.workflow_runs, item),
        active_workflow_run_id=active_id,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_workflow_runs_loaded(state: AppState, event: Event) -> AppState:
    """Hydrate workflow_runs feed from persisted metadata on startup."""
    if event.topic != WORKFLOW_RUNS_LOADED:
        return state
    raw_runs = event.payload.get("runs")
    if not isinstance(raw_runs, list) or not raw_runs:
        return state

    runs = state.workflow_runs
    for raw in raw_runs:
        if not isinstance(raw, dict):
            continue
        run_id = str(raw.get("run_id", ""))
        if not run_id or _find_workflow_run(runs, run_id) is not None:
            continue
        item = WorkflowRunItem(
            run_id=run_id,
            workflow_id=str(raw.get("workflow_id", "")),
            state=str(raw.get("state", "completed")),
            current_step_index=_coerce_int(raw.get("current_step_index"), 0),
            total_steps=_coerce_int(raw.get("total_steps"), 0),
            error=str(raw.get("error", "")),
        )
        runs = _upsert_workflow_run(runs, item)

    return replace(
        state,
        workflow_runs=runs,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_permission_check(state: AppState, event: Event) -> AppState:
    """Project interactive permission checks for UI approval flow."""
    if event.topic == PERMISSION_CHECK_REQUEST:
        payload = event.payload
        if not payload.get("interactive"):
            return state
        check_id = str(payload.get("check_id", ""))
        if not check_id:
            return state
        perms = tuple(str(p) for p in (payload.get("permissions") or []) if p)
        item = PermissionCheckItem(
            check_id=check_id,
            permissions=perms,
            actor_type=str(payload.get("actor_type", "agent")),
            actor_id=str(payload.get("actor_id") or ""),
            summary=str(payload.get("summary") or "An agent requested supervised permissions."),
            interactive=True,
        )
        return replace(
            state,
            pending_permission_check=item,
            permission_check_revision=state.permission_check_revision + 1,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )

    if event.topic == PERMISSION_CHECK_RESULT:
        result_id = str(event.payload.get("check_id", ""))
        pending = state.pending_permission_check
        if pending is None or pending.check_id != result_id:
            return state
        return replace(
            state,
            pending_permission_check=None,
            permission_check_revision=state.permission_check_revision + 1,
            last_event_topic=event.topic,
            last_event_source=event.source,
        )

    return state


from ai_command_center.core.state.chat_state import (  # noqa: E402
    _is_pending_chat_user_text as _chat_is_pending_user_text,
    _reduce_chat_cancelled,
    _reduce_chat_chunk,
    _reduce_chat_complete,
    _reduce_chat_error,
    _reduce_chat_history_loaded,
    _reduce_chat_started,
    _reduce_chat_workspace_entity,
    _reduce_command_routed,
    _reduce_context_snapshot,
    _reduce_ui_chat_new_session,
)
from ai_command_center.core.state.workspace_state import (  # noqa: E402
    _reduce_notes_indexed,
    _reduce_workspace_active,
    _reduce_workspace_os_event,
    _reduce_workspace_selection,
)
from ai_command_center.core.state.model_state import (  # noqa: E402
    MODEL_REDUCERS,
)
from ai_command_center.core.state.tool_state import (  # noqa: E402
    TOOL_REDUCERS,
)


def _is_pending_chat_user_text(text: str) -> bool:
    """Compatibility wrapper for tests and diagnostics."""
    return _chat_is_pending_user_text(text)

def _reduce_orchestration_run(state: AppState, event: Event) -> AppState:
    if event.topic != ORCHESTRATION_RUN_SNAPSHOT:
        return state
    payload = event.payload
    facts = payload.get("execution_facts") or {}
    run = OrchestrationRunSnapshot(
        request_id=str(payload.get("request_id", "")),
        query=str(payload.get("query", "")),
        intent=str(payload.get("intent", "")),
        provider_id=str(payload.get("provider_id", "")),
        execution_success=bool(payload.get("execution_success")),
        execution_facts=dict(facts) if isinstance(facts, dict) else {},
        execution_error=str(payload.get("execution_error") or "") or None,
        truth_valid=bool(payload.get("truth_valid")),
        truth_detail=str(payload.get("truth_detail", "")),
        response_source=str(payload.get("response_source", "")),
        response_text=str(payload.get("response_text", "")),
        receipt_id=str(payload.get("receipt_id", "")),
        trace_id=str(payload.get("trace_id", "")),
        span_id=str(payload.get("span_id", "")),
    )
    exec_ctx = ExecutionContext(
        request_id=run.request_id,
        provider_id=run.provider_id,
        status="ready" if run.execution_success else "error",
        intent=run.intent,
        query=run.query,
        response_source=run.response_source,
        truth_valid=run.truth_valid,
        truth_detail=run.truth_detail,
        trace_spans=(
            SpanItem(
                span_id=run.span_id or run.request_id,
                name=run.intent or "orchestration",
                kind="orchestration",
                status="ok" if run.execution_success else "error",
            ),
        ),
        metrics={"receipt_id": run.receipt_id, "trace_id": run.trace_id},
    )
    return replace(
        state,
        orchestration_run=run,
        execution_context=exec_ctx,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_execution_context(state: AppState, event: Event) -> AppState:
    new_ctx = reduce_execution_query_result(state.execution_context, event)
    if new_ctx == state.execution_context:
        return state
    return replace(
        state,
        execution_context=new_ctx,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_execution_timeline(state: AppState, event: Event) -> AppState:
    new_timeline = reduce_execution_timeline_state(state.execution_timeline, event)
    if new_timeline == state.execution_timeline:
        return state
    return replace(
        state,
        execution_timeline=new_timeline,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_inspector(state: AppState, event: Event) -> AppState:
    new_inspector = reduce_inspector_state(state.inspector, event)
    if new_inspector == state.inspector:
        return state
    return replace(
        state,
        inspector=new_inspector,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_workflow_graph(state: AppState, event: Event) -> AppState:
    new_graph = reduce_workflow_graph_state(state.workflow_graph, event)
    if new_graph == state.workflow_graph:
        return state
    return replace(
        state,
        workflow_graph=new_graph,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_automation_workspace(state: AppState, event: Event) -> AppState:
    new_workspace = reduce_automation_workspace_state(state, event)
    if new_workspace == state:
        return state
    return replace(
        new_workspace,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _trim_dict_feed(
    feed: tuple[dict[str, object], ...],
    item: dict[str, object],
    *,
    limit: int = 20,
) -> tuple[dict[str, object], ...]:
    return (item, *feed)[:limit]


def _reduce_brain_state(state: AppState, event: Event) -> AppState:
    payload = dict(event.payload)
    if event.topic == KERNEL_STATE_CHANGED:
        return replace(
            state,
            brain_kernel_state=str(payload.get("to") or state.brain_kernel_state),
            last_event_topic=event.topic,
            last_event_source=event.source,
        )
    if event.topic in {
        GOAL_SUBMITTED,
        GOAL_ACTIVATED,
        GOAL_PAUSED,
        GOAL_RESUMED,
        GOAL_CANCELLED,
        GOAL_COMPLETED,
        GOAL_FAILED,
    }:
        goal_payload = payload.get("goal")
        goal_id = str(
            payload.get("goal_id")
            or (goal_payload.get("id") if isinstance(goal_payload, dict) else "")
            or ""
        )
        status = event.topic.removeprefix("goal.")
        item: dict[str, object] = {
            "topic": event.topic,
            "goal_id": goal_id,
            "status": status,
        }
        if isinstance(goal_payload, dict):
            item.update(goal_payload)
            item["goal_id"] = goal_id
            item["status"] = status
        return replace(
            state,
            brain_recent_goals=_trim_dict_feed(state.brain_recent_goals, item),
            last_event_topic=event.topic,
            last_event_source=event.source,
        )
    if event.topic == OBSERVATION_RECEIVED:
        item = {
            "id": str(payload.get("id", "")),
            "source": str(payload.get("source", "")),
            "subject": str(payload.get("subject", "")),
            "change_type": str(payload.get("change_type", "")),
        }
        return replace(
            state,
            brain_recent_observations=_trim_dict_feed(
                state.brain_recent_observations,
                item,
            ),
            last_event_topic=event.topic,
            last_event_source=event.source,
        )
    if event.topic in {
        RUNTIME_ACTION_STARTED,
        RUNTIME_APPROVAL_REQUESTED,
        RUNTIME_ACTION_COMPLETED,
        RUNTIME_ACTION_FAILED,
        RUNTIME_ACTION_DENIED,
    }:
        item = {
            "topic": event.topic,
            "action_id": str(payload.get("action_id", "")),
            "status": str(payload.get("status") or event.topic.removeprefix("runtime.")),
        }
        return replace(
            state,
            brain_recent_runtime_actions=_trim_dict_feed(
                state.brain_recent_runtime_actions,
                item,
            ),
            last_event_topic=event.topic,
            last_event_source=event.source,
        )
    return state


# ── Blueprint Phase 2 — World Model AppState reducer ────────────────────────────

_WM_MUTATION_TOPICS = frozenset({
    WORLD_MODEL_MUTATION_APPLIED,
    RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
})
_WM_TOPICS = _WM_MUTATION_TOPICS | frozenset({
    WORLD_MODEL_GRAPH_REFRESHED,
    WORLD_MODEL_NODE_SELECTED,
    WORLD_MODEL_NODE_DESELECTED,
    ENTITY_CREATED,
    ENTITY_UPDATED,
    ENTITY_DELETED,
    GOAL_SUBMITTED,
    GOAL_ACTIVATED,
    GOAL_COMPLETED,
    GOAL_FAILED,
    GOAL_CANCELLED,
})


def _reduce_world_model(state: AppState, event: Event) -> AppState:
    """Project world model events into immutable AppState.world_model snapshot."""
    topic = event.topic
    if topic not in _WM_TOPICS:
        return state
    wm = state.world_model
    p = event.payload

    if topic == WORLD_MODEL_GRAPH_REFRESHED:
        raw_nodes = p.get("nodes") or []
        raw_edges = p.get("edges") or []
        nodes = tuple(
            NodeSnapshot(
                node_id=str(n.get("id") or ""),
                node_type=str(n.get("type") or "resource"),
                label=str(n.get("label") or n.get("name") or ""),
                attributes=_attrs_to_pairs(n.get("attributes")),
            )
            for n in raw_nodes if n.get("id")
        )
        edges = tuple(
            EdgeSnapshot(
                edge_id=str(e.get("id") or ""),
                from_node_id=str(e.get("from_node_id") or ""),
                to_node_id=str(e.get("to_node_id") or ""),
                edge_type=str(e.get("type") or "related"),
                from_label=str(e.get("from_label") or ""),
                to_label=str(e.get("to_label") or ""),
            )
            for e in raw_edges
        )
        new_wm = replace(
            wm,
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
        )
        return replace(
            state,
            world_model=new_wm,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == ENTITY_CREATED:
        node_id = str(p.get("id") or p.get("entity_id") or "")
        if not node_id:
            return state
        new_node = NodeSnapshot(
            node_id=node_id,
            node_type=str(p.get("entity_type") or p.get("type") or "resource"),
            label=str(p.get("name") or p.get("title") or node_id),
            attributes=_attrs_to_pairs(p.get("attributes")),
        )
        nodes = tuple(n for n in wm.nodes if n.node_id != node_id) + (new_node,)
        new_wm = replace(wm, nodes=nodes, node_count=len(nodes))
        return replace(
            state,
            world_model=new_wm,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == ENTITY_UPDATED:
        node_id = str(p.get("id") or p.get("entity_id") or "")
        if not node_id:
            return state
        prev = next((n for n in wm.nodes if n.node_id == node_id), None)
        updated = NodeSnapshot(
            node_id=node_id,
            node_type=str(p.get("entity_type") or p.get("type") or (prev.node_type if prev else "resource")),
            label=str(p.get("name") or p.get("title") or (prev.label if prev else node_id)),
            attributes=_attrs_to_pairs(p.get("attributes")) or (prev.attributes if prev else ()),
        )
        nodes = tuple(n if n.node_id != node_id else updated for n in wm.nodes)
        if prev is None:
            nodes = nodes + (updated,)
        new_wm = replace(wm, nodes=nodes, node_count=len(nodes))
        return replace(
            state,
            world_model=new_wm,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == ENTITY_DELETED:
        node_id = str(p.get("id") or p.get("entity_id") or "")
        nodes = tuple(n for n in wm.nodes if n.node_id != node_id)
        edges = tuple(
            e for e in wm.edges
            if e.from_node_id != node_id and e.to_node_id != node_id
        )
        selected = "" if wm.selected_node_id == node_id else wm.selected_node_id
        new_wm = replace(wm, nodes=nodes, edges=edges, node_count=len(nodes), selected_node_id=selected)
        return replace(
            state,
            world_model=new_wm,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic in _WM_MUTATION_TOPICS:
        mutation = p.get("mutation") or p
        entry = MutationSnapshot(
            mutation_id=str(mutation.get("id") or mutation.get("mutation_id") or ""),
            mutation_type=str(mutation.get("type") or "unknown"),
            correlation_id=str(mutation.get("correlation_id") or ""),
            goal_id=str(mutation.get("goal_id") or ""),
            timestamp=str(mutation.get("created_at") or mutation.get("timestamp") or ""),
            summary=_wm_mutation_summary(mutation),
        )
        log = wm.mutation_log + (entry,)
        if len(log) > 200:
            log = log[-200:]
        new_wm = replace(wm, mutation_log=log, mutation_count=len(log))
        return replace(
            state,
            world_model=new_wm,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == WORLD_MODEL_NODE_SELECTED:
        node_id = str(p.get("node_id") or "")
        new_wm = replace(wm, selected_node_id=node_id)
        return replace(
            state,
            world_model=new_wm,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == WORLD_MODEL_NODE_DESELECTED:
        new_wm = replace(wm, selected_node_id="")
        return replace(
            state,
            world_model=new_wm,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic in {GOAL_SUBMITTED, GOAL_ACTIVATED, GOAL_COMPLETED, GOAL_FAILED, GOAL_CANCELLED}:
        goal = p.get("goal") or p
        goal_id = str(goal.get("id") or goal.get("goal_id") or p.get("goal_id") or "")
        if not goal_id:
            return state
        status_map = {
            GOAL_SUBMITTED: "submitted",
            GOAL_ACTIVATED: "active",
            GOAL_COMPLETED: "complete",
            GOAL_FAILED: "failed",
            GOAL_CANCELLED: "cancelled",
        }
        snap = GoalSnapshot(
            goal_id=goal_id,
            title=str(goal.get("title") or goal_id),
            status=str(goal.get("status") or status_map.get(topic, "submitted")),
        )
        goals = tuple(g if g.goal_id != goal_id else snap for g in wm.goals)
        if not any(g.goal_id == goal_id for g in wm.goals):
            goals = goals + (snap,)
        new_wm = replace(wm, goals=goals)
        return replace(
            state,
            world_model=new_wm,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    return state


def _wm_mutation_summary(mutation: dict) -> str:
    mtype = str(mutation.get("type") or "")
    payload = mutation.get("payload") or {}
    node = payload.get("node") or {}
    node_id = str(node.get("id") or payload.get("node_id") or "")
    edge_id = str(payload.get("edge_id") or "")
    if node_id:
        return f"{mtype} → node:{node_id}"
    if edge_id:
        return f"{mtype} → edge:{edge_id}"
    return mtype


# ── Blueprint Phase 8 — Permission Check AppState reducer ─────────────────────

_PERMISSION_TOPICS = frozenset({
    PERMISSION_CHECK_REQUEST,
    PERMISSION_CHECK_RESULT,
})


def _reduce_permission_snapshot(state: AppState, event: Event) -> AppState:
    """Project permission check events into immutable AppState.permission_snapshot."""
    topic = event.topic
    if topic not in _PERMISSION_TOPICS:
        return state
    p = event.payload
    snap = state.permission_snapshot

    if topic == PERMISSION_CHECK_REQUEST:
        if not p.get("interactive"):
            return state
        check_id = str(p.get("check_id") or "")
        if not check_id:
            return state
        pending = PendingCheck(
            check_id=check_id,
            permissions=tuple(str(x) for x in (p.get("permissions") or []) if x),
            actor_type=str(p.get("actor_type") or "agent"),
            actor_id=str(p.get("actor_id") or ""),
            summary=str(p.get("summary") or "An agent requested supervised permissions."),
        )
        new_snap = replace(
            snap,
            pending=pending,
            revision=snap.revision + 1,
            total_requested=snap.total_requested + 1,
        )
        return replace(
            state,
            permission_snapshot=new_snap,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == PERMISSION_CHECK_RESULT:
        check_id = str(p.get("check_id") or "")
        pending = snap.pending
        if pending is None or pending.check_id != check_id:
            return state
        granted = bool(p.get("granted", False))
        resolved = ResolvedCheck(
            check_id=check_id,
            actor_id=pending.actor_id,
            granted=granted,
            summary=pending.summary,
        )
        history = (resolved,) + snap.resolved
        if len(history) > _MAX_RESOLVED_HISTORY:
            history = history[:_MAX_RESOLVED_HISTORY]
        new_snap = replace(
            snap,
            pending=None,
            revision=snap.revision + 1,
            resolved=history,
            total_granted=snap.total_granted + (1 if granted else 0),
            total_denied=snap.total_denied + (0 if granted else 1),
        )
        return replace(
            state,
            permission_snapshot=new_snap,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    return state


# ── Blueprint Phase 7 — Workflow Library AppState reducer ─────────────────────

_WORKFLOW_LIB_TOPICS = frozenset({
    WORKFLOW_STARTED,
    WORKFLOW_STEP_STARTED,
    WORKFLOW_STEP_COMPLETED,
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_RUNS_LOADED,
})


def _reduce_workflow_library(state: AppState, event: Event) -> AppState:
    """Project workflow lifecycle events into immutable AppState.workflow_library."""
    topic = event.topic
    if topic not in _WORKFLOW_LIB_TOPICS:
        return state
    p = event.payload
    lib = state.workflow_library

    # ── WORKFLOW_RUNS_LOADED (bulk hydration on startup) ───────────────────────
    if topic == WORKFLOW_RUNS_LOADED:
        raw_runs = p.get("runs")
        if not isinstance(raw_runs, list) or not raw_runs:
            return state
        run_map: dict[str, WorkflowRunSnapshot] = {r.run_id: r for r in lib.runs}
        for raw in raw_runs:
            if not isinstance(raw, dict):
                continue
            run_id = str(raw.get("run_id") or "")
            if not run_id or run_id in run_map:
                continue
            run_map[run_id] = WorkflowRunSnapshot(
                run_id=run_id,
                workflow_id=str(raw.get("workflow_id") or ""),
                state=str(raw.get("state") or "completed"),
                current_step_index=int(raw.get("current_step_index") or 0),
                total_steps=int(raw.get("total_steps") or 0),
                error=str(raw.get("error") or ""),
            )
        runs = tuple(run_map.values())
        if len(runs) > _MAX_WORKFLOW_HISTORY:
            runs = runs[:_MAX_WORKFLOW_HISTORY]
        new_lib = replace(lib, runs=runs, total_started=lib.total_started + len(run_map) - len(lib.runs))
        return replace(
            state,
            workflow_library=new_lib,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    run_id = str(p.get("run_id") or "")
    if not run_id:
        return state

    prev = lib.run_by_id(run_id)

    # ── WORKFLOW_STARTED ───────────────────────────────────────────────────────
    if topic == WORKFLOW_STARTED:
        workflow_id = str(p.get("workflow_id") or "")
        total_steps = int(p.get("total_steps") or 0)
        run = WorkflowRunSnapshot(
            run_id=run_id,
            workflow_id=workflow_id,
            state="running",
            total_steps=total_steps,
        )
        runs = lib.runs
        if not any(r.run_id == run_id for r in runs):
            runs = runs + (run,)
            if len(runs) > _MAX_WORKFLOW_HISTORY:
                runs = runs[:_MAX_WORKFLOW_HISTORY]
        else:
            runs = tuple(r if r.run_id != run_id else run for r in runs)
        is_new_run = not any(r.run_id == run_id for r in lib.runs)
        new_lib = replace(
            lib,
            runs=runs,
            active_run_id=run_id,
            total_started=lib.total_started + (1 if is_new_run else 0),
        )
        return replace(
            state,
            workflow_library=new_lib,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if prev is None:
        prev = WorkflowRunSnapshot(run_id=run_id, state="running")

    # ── WORKFLOW_STEP_STARTED ──────────────────────────────────────────────────
    if topic == WORKFLOW_STEP_STARTED:
        step_id = str(p.get("step_id") or "")
        step_index = int(p.get("index") or prev.current_step_index)
        step = WorkflowStepSnapshot(
            step_id=step_id,
            run_id=run_id,
            index=step_index,
            status="running",
        )
        steps = prev.steps
        if not any(s.step_id == step_id for s in steps):
            steps = steps + (step,)
        else:
            steps = tuple(s if s.step_id != step_id else step for s in steps)
        run = replace(
            prev,
            state="running",
            current_step_id=step_id,
            current_step_index=step_index,
            steps=steps,
        )

    # ── WORKFLOW_STEP_COMPLETED ────────────────────────────────────────────────
    elif topic == WORKFLOW_STEP_COMPLETED:
        step_id = str(p.get("step_id") or prev.current_step_id)
        steps = tuple(
            replace(s, status="completed") if s.step_id == step_id else s
            for s in prev.steps
        )
        run = replace(
            prev,
            steps=steps,
            current_step_index=prev.current_step_index + 1,
        )

    # ── WORKFLOW_COMPLETED / WORKFLOW_FAILED ───────────────────────────────────
    elif topic in {WORKFLOW_COMPLETED, WORKFLOW_FAILED}:
        final_state = "completed" if topic == WORKFLOW_COMPLETED else "failed"
        error = str(p.get("error") or "") if topic == WORKFLOW_FAILED else ""
        run = replace(prev, state=final_state, error=error)

    else:
        return state

    runs = tuple(r if r.run_id != run_id else run for r in lib.runs)
    if not any(r.run_id == run_id for r in lib.runs):
        runs = lib.runs + (run,)

    active_id = lib.active_run_id
    total_completed = lib.total_completed
    total_failed = lib.total_failed
    if topic == WORKFLOW_COMPLETED:
        total_completed += 1
        if active_id == run_id:
            active_id = ""
    elif topic == WORKFLOW_FAILED:
        total_failed += 1
        if active_id == run_id:
            active_id = ""

    new_lib = replace(
        lib,
        runs=runs,
        active_run_id=active_id,
        total_completed=total_completed,
        total_failed=total_failed,
    )
    return replace(
        state,
        workflow_library=new_lib,
        last_event_topic=topic,
        last_event_source=event.source,
    )


# ── Blueprint Phase 6 — Provider Registry AppState reducer ────────────────────

_PROVIDER_REGISTRY_TOPICS = frozenset({
    CAPABILITY_PROVIDERS_READY,
    ORCHESTRATION_PROVIDER_HEALTH,
})


def _reduce_provider_registry(state: AppState, event: Event) -> AppState:
    """Project provider health/runtime events into immutable AppState.provider_registry."""
    topic = event.topic
    if topic not in _PROVIDER_REGISTRY_TOPICS:
        return state
    p = event.payload
    reg = state.provider_registry
    entry_map: dict[str, ProviderRegistryEntry] = {e.provider_id: e for e in reg.providers}

    if topic == CAPABILITY_PROVIDERS_READY:
        for item in (p.get("providers") or []):
            if not isinstance(item, dict):
                continue
            pid = str(item.get("id") or "")
            if not pid:
                continue
            prev = entry_map.get(pid)
            health_raw = str(item.get("health_state") or "").lower()
            if health_raw in {"ready", "healthy"}:
                health_status = "healthy"
            elif health_raw == "degraded":
                health_status = "degraded"
            else:
                health_status = prev.health_status if prev else "offline"
            entry_map[pid] = ProviderRegistryEntry(
                provider_id=pid,
                name=str(item.get("name") or pid),
                version=str(item.get("version") or (prev.version if prev else "")),
                source="runtime",
                kind=str(item.get("kind") or (prev.kind if prev else "")),
                health_status=health_status,
                health_detail=str(item.get("health_detail") or ""),
                enabled=bool(item.get("enabled", True)),
                capabilities=tuple(str(c) for c in (item.get("capabilities") or [])),
                permissions=tuple(str(q) for q in (item.get("permissions") or [])),
            )

    elif topic == ORCHESTRATION_PROVIDER_HEALTH:
        pid = str(p.get("provider_id") or "")
        if not pid:
            return state
        prev = entry_map.get(pid)
        healthy = bool(p.get("healthy", False))
        health_status = "healthy" if healthy else "offline"
        entry_map[pid] = ProviderRegistryEntry(
            provider_id=pid,
            name=str(p.get("display_name") or (prev.name if prev else pid)),
            version=prev.version if prev else "",
            source="orchestration",
            kind=prev.kind if prev else "",
            health_status=health_status,
            health_detail=str(p.get("detail") or ""),
            enabled=prev.enabled if prev else True,
            capabilities=prev.capabilities if prev else (),
            permissions=prev.permissions if prev else (),
        )

    providers = tuple(entry_map.values())
    healthy_count = sum(1 for e in providers if e.healthy)
    degraded_count = sum(1 for e in providers if e.degraded)
    new_reg = ProviderRegistrySnapshot(
        providers=providers,
        total_count=len(providers),
        healthy_count=healthy_count,
        degraded_count=degraded_count,
    )
    return replace(
        state,
        provider_registry=new_reg,
        last_event_topic=topic,
        last_event_source=event.source,
    )


# ── Blueprint Phase 5 — Agent Pipeline AppState reducer ───────────────────────

_AGENT_TOPICS = frozenset({
    AGENT_SPAWNED,
    AGENT_TASK_REQUEST,
    AGENT_TASK_COMPLETE,
    AGENT_TERMINATED,
    AGENT_PIPELINE_STARTED,
    AGENT_PIPELINE_STAGE,
    AGENT_PIPELINE_PLANNED,
    AGENT_PIPELINE_COMPLETE,
})


def _reduce_agent_pipeline_snapshot(state: AppState, event: Event) -> AppState:
    """Project agent/pipeline events into immutable AppState.agent_pipeline snapshot."""
    topic = event.topic
    if topic not in _AGENT_TOPICS:
        return state
    p = event.payload
    ap = state.agent_pipeline

    if topic in {AGENT_SPAWNED, AGENT_TASK_REQUEST, AGENT_TASK_COMPLETE, AGENT_TERMINATED}:
        agent_id = str(p.get("agent_id") or "")
        if not agent_id:
            return state

        prev = ap.run_by_id(agent_id)
        request_id = str(p.get("request_id") or (prev.request_id if prev else ""))
        task = str(p.get("task") or (prev.task if prev else ""))
        workspace_id = str(p.get("workspace_id") or (prev.workspace_id if prev else ""))
        workspace_entity_id = str(
            p.get("workspace_entity_id") or (prev.workspace_entity_id if prev else "")
        )
        spawn_role = str(p.get("spawn_role") or (prev.spawn_role if prev else ""))

        if topic == AGENT_SPAWNED:
            run_state = str(p.get("state") or "spawning")
            steps = prev.steps if prev else 0
            error = ""
        elif topic == AGENT_TASK_REQUEST:
            run_state = "running"
            steps = (prev.steps if prev else 0) + 1
            error = str(p.get("error") or (prev.error if prev else ""))
        elif topic == AGENT_TASK_COMPLETE:
            run_state = "waiting"
            steps = prev.steps if prev else 0
            error = str(p.get("error") or (prev.error if prev else ""))
        else:  # AGENT_TERMINATED
            error = str(p.get("error") or "")
            run_state = "failed" if error else "terminated"
            steps = prev.steps if prev else 0

        run = AgentRunSnapshot(
            agent_id=agent_id,
            request_id=request_id,
            state=run_state,
            task=task or (prev.task if prev else ""),
            error=error,
            steps=steps,
            workspace_id=workspace_id or (prev.workspace_id if prev else ""),
            workspace_entity_id=workspace_entity_id or (prev.workspace_entity_id if prev else ""),
            spawn_role=spawn_role or (prev.spawn_role if prev else ""),
        )

        runs = tuple(r if r.agent_id != agent_id else run for r in ap.runs)
        if not any(r.agent_id == agent_id for r in ap.runs):
            runs = ap.runs + (run,)

        if topic == AGENT_TERMINATED:
            active_ids = tuple(i for i in ap.active_run_ids if i != agent_id)
            active_id = active_ids[0] if active_ids and ap.active_run_id == agent_id else (
                ap.active_run_id if ap.active_run_id != agent_id else ""
            )
        else:
            existing_ids = ap.active_run_ids
            active_ids = existing_ids if agent_id in existing_ids else existing_ids + (agent_id,)
            active_id = agent_id

        total = ap.total_spawned + (1 if topic == AGENT_SPAWNED else 0)
        new_ap = replace(
            ap,
            runs=runs,
            active_run_id=active_id,
            active_run_ids=active_ids,
            total_spawned=total,
        )
        return replace(
            state,
            agent_pipeline=new_ap,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == AGENT_PIPELINE_STARTED:
        pipeline_id = str(p.get("pipeline_id") or "")
        stage = str(p.get("stage") or "starting")
        planned_raw = p.get("planned_tools") or ()
        planned = tuple(str(t) for t in planned_raw)
        new_ap = replace(ap, pipeline_id=pipeline_id, pipeline_stage=stage, planned_tools=planned)
        return replace(
            state,
            agent_pipeline=new_ap,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == AGENT_PIPELINE_STAGE:
        pipeline_id = str(p.get("pipeline_id") or ap.pipeline_id)
        stage = str(p.get("stage") or "")
        new_ap = replace(ap, pipeline_id=pipeline_id, pipeline_stage=stage)
        return replace(
            state,
            agent_pipeline=new_ap,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == AGENT_PIPELINE_PLANNED:
        planned_raw = p.get("planned_tools") or ()
        planned = tuple(str(t) for t in planned_raw) or ap.planned_tools
        new_ap = replace(ap, planned_tools=planned)
        return replace(
            state,
            agent_pipeline=new_ap,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == AGENT_PIPELINE_COMPLETE:
        new_ap = replace(ap, pipeline_id="", pipeline_stage="complete", planned_tools=())
        return replace(
            state,
            agent_pipeline=new_ap,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    return state


# ── Blueprint Phase 4 — Execution Library AppState reducer ────────────────────

_EXEC_LIB_TOPICS = frozenset({
    EXECUTION_RUN_STARTED,
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    EXECUTION_STEP_STARTED,
    EXECUTION_STEP_COMPLETED,
    EXECUTION_STEP_FAILED,
    EXECUTION_STEP_AWAITING_APPROVAL,
})


def _reduce_execution_library(state: AppState, event: Event) -> AppState:
    """Project execution events into immutable AppState.execution_library snapshot."""
    topic = event.topic
    if topic not in _EXEC_LIB_TOPICS:
        return state
    p = event.payload
    lib = state.execution_library
    plan = lib.active_plan

    if topic == EXECUTION_RUN_STARTED:
        raw_steps = p.get("steps") or []
        steps = tuple(
            ExecutionStepSnapshot(
                step_id=str(s.get("step_id") or ""),
                run_id=str(p.get("run_id") or ""),
                index=int(s.get("index") or i),
                capability=str(s.get("capability") or ""),
                risk=str(s.get("risk") or ""),
                status="pending",
            )
            for i, s in enumerate(raw_steps)
            if isinstance(s, dict)
        )
        new_plan = ExecutionPlanSnapshot(
            run_id=str(p.get("run_id") or ""),
            request_id=str(p.get("request_id") or ""),
            goal=str(p.get("goal") or ""),
            total_steps=int(p.get("total_steps") or len(steps)),
            status="running",
            steps=steps,
        )
        new_lib = replace(lib, active_plan=new_plan)
        return replace(
            state,
            execution_library=new_lib,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic in {EXECUTION_STEP_STARTED, EXECUTION_STEP_AWAITING_APPROVAL}:
        step_id = str(p.get("step_id") or "")
        step_status = "awaiting_approval" if topic == EXECUTION_STEP_AWAITING_APPROVAL else "started"
        updated_steps = tuple(
            replace(s, status=step_status) if s.step_id == step_id else s
            for s in plan.steps
        )
        if not any(s.step_id == step_id for s in plan.steps):
            new_step = ExecutionStepSnapshot(
                step_id=step_id,
                run_id=str(p.get("run_id") or plan.run_id),
                index=int(p.get("index") or 0),
                capability=str(p.get("capability") or ""),
                risk=str(p.get("risk") or ""),
                status=step_status,
            )
            updated_steps = plan.steps + (new_step,)
        new_plan = replace(plan, steps=updated_steps, current_step_id=step_id)
        new_lib = replace(lib, active_plan=new_plan)
        return replace(
            state,
            execution_library=new_lib,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == EXECUTION_STEP_COMPLETED:
        step_id = str(p.get("step_id") or "")
        updated_steps = tuple(
            replace(s, status="completed") if s.step_id == step_id else s
            for s in plan.steps
        )
        new_plan = replace(plan, steps=updated_steps)
        new_lib = replace(lib, active_plan=new_plan)
        return replace(
            state,
            execution_library=new_lib,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == EXECUTION_STEP_FAILED:
        step_id = str(p.get("step_id") or "")
        error = str(p.get("error") or "")
        updated_steps = tuple(
            replace(s, status="failed", error=error) if s.step_id == step_id else s
            for s in plan.steps
        )
        new_plan = replace(plan, steps=updated_steps, status="failed", error=error)
        new_lib = replace(lib, active_plan=new_plan)
        return replace(
            state,
            execution_library=new_lib,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic in {EXECUTION_RUN_COMPLETE, EXECUTION_RUN_FAILED}:
        final_status = "complete" if topic == EXECUTION_RUN_COMPLETE else "failed"
        error = str(p.get("error") or "") if topic == EXECUTION_RUN_FAILED else ""
        entry = ExecutionRunEntry(
            run_id=plan.run_id or str(p.get("run_id") or ""),
            request_id=plan.request_id or str(p.get("request_id") or ""),
            source="orchestration",
            created_at=float(p.get("created_at") or 0.0),
            summary=plan.goal[:120] if plan.goal else "",
            status=final_status,
        )
        history = (entry,) + lib.run_history
        if len(history) > _MAX_RUN_HISTORY:
            history = history[:_MAX_RUN_HISTORY]
        closed_plan = replace(
            plan,
            status=final_status,
            error=error,
            current_step_id="" if topic == EXECUTION_RUN_COMPLETE else plan.current_step_id,
        )
        new_lib = replace(
            lib,
            active_plan=closed_plan,
            run_history=history,
            total_runs=lib.total_runs + 1,
        )
        return replace(
            state,
            execution_library=new_lib,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    return state


# ── Blueprint Phase 3 — Capability Library AppState reducer ───────────────────

_CAP_LIB_TOPICS = frozenset({
    CAPABILITY_PROVIDERS_READY,
    CAPABILITY_LIFECYCLE_SNAPSHOT,
    CAPABILITY_CATALOG_RESULT,
})


def _reduce_capability_library(state: AppState, event: Event) -> AppState:
    """Project capability events into immutable AppState.capability_library snapshot."""
    topic = event.topic
    if topic not in _CAP_LIB_TOPICS:
        return state
    p = event.payload
    lib = state.capability_library

    if topic == CAPABILITY_LIFECYCLE_SNAPSHOT:
        raw_records = p.get("capability_lifecycle") or []
        entry_map: dict[str, CapabilityEntry] = {e.capability_id: e for e in lib.entries}
        for item in raw_records:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("capability_id") or "")
            if not cid:
                continue
            prev = entry_map.get(cid)
            raw_params = item.get("parameters") or {}
            params: tuple[tuple[str, str], ...] = ()
            if isinstance(raw_params, dict):
                params = tuple((str(k), str(v)) for k, v in raw_params.items())
            entry_map[cid] = CapabilityEntry(
                capability_id=cid,
                provider_id=str(item.get("provider_id") or (prev.provider_id if prev else "")),
                capability_kind=str(item.get("capability_kind") or (prev.capability_kind if prev else "")),
                lifecycle_state=str(item.get("lifecycle_state") or (prev.lifecycle_state if prev else "discovered")),
                health_status=str(item.get("health_status") or (prev.health_status if prev else "offline")),
                certified=bool(item.get("certified", prev.certified if prev else False)),
                observable=bool(item.get("observable", prev.observable if prev else False)),
                source=str(item.get("source") or (prev.source if prev else "")),
                description=prev.description if prev else "",
                parameters=params or (prev.parameters if prev else ()),
                last_error=str(item.get("last_error") or ""),
                discovered_at=float(item.get("discovered_at") or (prev.discovered_at if prev else 0.0)),
                updated_at=float(item.get("updated_at") or (prev.updated_at if prev else 0.0)),
            )
        entries = tuple(entry_map.values())
        healthy = sum(1 for e in entries if e.health_status == "healthy")
        new_lib = replace(
            lib,
            entries=entries,
            total_count=len(entries),
            healthy_count=healthy,
        )
        return replace(
            state,
            capability_library=new_lib,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == CAPABILITY_CATALOG_RESULT:
        raw_specs = p.get("specs") or []
        entry_map = {e.capability_id: e for e in lib.entries}
        for spec in raw_specs:
            if not isinstance(spec, dict):
                continue
            cid = str(spec.get("capability_id") or spec.get("id") or "")
            if not cid:
                continue
            prev = entry_map.get(cid)
            raw_params = spec.get("parameters") or {}
            params = ()
            if isinstance(raw_params, dict):
                params = tuple((str(k), str(v)) for k, v in raw_params.items())
            entry_map[cid] = CapabilityEntry(
                capability_id=cid,
                provider_id=str(spec.get("provider_id") or (prev.provider_id if prev else "")),
                capability_kind=str(spec.get("kind") or spec.get("capability_kind") or (prev.capability_kind if prev else "")),
                lifecycle_state=prev.lifecycle_state if prev else "discovered",
                health_status=prev.health_status if prev else "offline",
                certified=prev.certified if prev else False,
                observable=prev.observable if prev else False,
                source=str(spec.get("source") or (prev.source if prev else "")),
                description=str(spec.get("description") or (prev.description if prev else "")),
                parameters=params or (prev.parameters if prev else ()),
                last_error=prev.last_error if prev else "",
                discovered_at=prev.discovered_at if prev else 0.0,
                updated_at=prev.updated_at if prev else 0.0,
            )
        entries = tuple(entry_map.values())
        healthy = sum(1 for e in entries if e.health_status == "healthy")
        new_lib = replace(
            lib,
            entries=entries,
            total_count=len(entries),
            healthy_count=healthy,
            catalog_version=lib.catalog_version + 1,
        )
        return replace(
            state,
            capability_library=new_lib,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    if topic == CAPABILITY_PROVIDERS_READY:
        raw_providers = p.get("providers") or []
        provider_map: dict[str, ProviderEntry] = {pr.provider_id: pr for pr in lib.providers}
        entry_map = {e.capability_id: e for e in lib.entries}
        for item in raw_providers:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("id") or "")
            if not pid:
                continue
            caps = [str(c) for c in (item.get("capabilities") or [])]
            provider_map[pid] = ProviderEntry(
                provider_id=pid,
                name=str(item.get("name") or pid),
                version=str(item.get("version") or ""),
                health_state=str(item.get("health_state") or ""),
                enabled=bool(item.get("enabled", True)),
                capability_count=len(caps),
            )
            for cid in caps:
                prev = entry_map.get(cid)
                entry_map[cid] = CapabilityEntry(
                    capability_id=cid,
                    provider_id=pid,
                    capability_kind=prev.capability_kind if prev else "",
                    lifecycle_state=prev.lifecycle_state if prev else "discovered",
                    health_status=str(item.get("health_state") or (prev.health_status if prev else "offline")),
                    certified=prev.certified if prev else False,
                    observable=prev.observable if prev else False,
                    source=prev.source if prev else "runtime",
                    description=prev.description if prev else "",
                    parameters=prev.parameters if prev else (),
                    last_error=prev.last_error if prev else "",
                    discovered_at=prev.discovered_at if prev else 0.0,
                    updated_at=prev.updated_at if prev else 0.0,
                )
        entries = tuple(entry_map.values())
        healthy = sum(1 for e in entries if e.health_status == "healthy")
        new_lib = replace(
            lib,
            entries=entries,
            providers=tuple(provider_map.values()),
            total_count=len(entries),
            healthy_count=healthy,
        )
        return replace(
            state,
            capability_library=new_lib,
            last_event_topic=topic,
            last_event_source=event.source,
        )

    return state


# ── Blueprint Phase 1 — Operations Library & Journal reducers ─────────────────

JOURNAL_MAX_ENTRIES = 500


def _reduce_operation_saved(state: AppState, event: Event) -> AppState:
    """Update operation_library_index from OPERATION_SAVED events."""
    if event.topic != OPERATION_SAVED:
        return state
    payload = event.payload
    correlation_id = str(payload.get("correlation_id", ""))
    if not correlation_id:
        return state
    existing_map = {s.correlation_id: s for s in state.operation_library_index}
    prev = existing_map.get(correlation_id)
    updated = OperationSnapshot(
        correlation_id=correlation_id,
        goal_id=str(payload.get("goal_id", prev.goal_id if prev else "")),
        goal_title=str(payload.get("goal_title", prev.goal_title if prev else "")),
        goal_status=str(payload.get("goal_status", prev.goal_status if prev else "unknown")),
        goal_priority=prev.goal_priority if prev else "normal",
        started_at=prev.started_at if prev else 0.0,
        completed_at=prev.completed_at if prev else 0.0,
        agent_ids=prev.agent_ids if prev else (),
        execution_ids=prev.execution_ids if prev else (),
        tags=prev.tags if prev else (),
    )
    existing_map[correlation_id] = updated
    index = tuple(
        sorted(existing_map.values(), key=lambda s: s.started_at or 0.0, reverse=True)
    )
    return replace(
        state,
        operation_library_index=index,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_operation_loaded(state: AppState, event: Event) -> AppState:
    """Set active_operation from OPERATION_LOADED payload snapshot."""
    if event.topic != OPERATION_LOADED:
        return state
    payload = event.payload
    raw_snapshot = payload.get("snapshot")
    if not isinstance(raw_snapshot, dict):
        return state
    try:
        snapshot = OperationSnapshot.from_dict(raw_snapshot)
    except Exception:
        return state
    return replace(
        state,
        active_operation=snapshot,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


def _reduce_journal_entry_appended(state: AppState, event: Event) -> AppState:
    """Append a JournalEntry to operation_journal, capped at JOURNAL_MAX_ENTRIES."""
    if event.topic != JOURNAL_ENTRY_APPENDED:
        return state
    counter = state.journal_entry_counter + 1
    try:
        entry = JournalEntry.from_payload(event.payload, entry_id=counter)
    except Exception:
        return state
    journal = state.operation_journal + (entry,)
    if len(journal) > JOURNAL_MAX_ENTRIES:
        journal = journal[-JOURNAL_MAX_ENTRIES:]
    return replace(
        state,
        operation_journal=journal,
        journal_entry_counter=counter,
        last_event_topic=event.topic,
        last_event_source=event.source,
    )


_DEFAULT_REDUCERS: tuple[Reducer, ...] = (
    _reduce_service_state,
    _reduce_settings_changed,
    _reduce_settings_snapshot,
    _reduce_command_routed,
    _reduce_chat_started,
    _reduce_chat_chunk,
    _reduce_chat_complete,
    _reduce_chat_cancelled,
    _reduce_chat_error,
    _reduce_chat_history_loaded,
    _reduce_context_snapshot,
    _reduce_error,
    _reduce_phase,
    _reduce_system_snapshot,
    _reduce_chat_workspace_entity,
    _reduce_ui_chat_new_session,
    _reduce_workspace_os_event,
    _reduce_workspace_active,
    _reduce_workspace_selection,
    _reduce_note_results,
    _reduce_note_selected,
    _reduce_note_created,
    _reduce_note_index_complete,
    _reduce_notes_indexed,
    _reduce_memory_stored,
    _reduce_memory_selected,
    _reduce_memory_cleared,
    _reduce_workspace_memory_catalog,
    _reduce_plugin_catalog,
    _reduce_capability_providers_ready,
    _reduce_capability_lifecycle_snapshot,
    _reduce_capability_prompt_catalog,
    _reduce_planner_last_plan,
    _reduce_execution_orchestrator,
    _reduce_orchestration_provider_health,
    _reduce_execution_run_feed,
    _reduce_plugin_state_changed,
    _reduce_agent_run,
    _reduce_agent_pipeline,
    _reduce_workflow_run,
    _reduce_workflow_runs_loaded,
    _reduce_permission_check,
    _reduce_orchestration_run,
    _reduce_execution_context,
    _reduce_execution_timeline,
    _reduce_inspector,
    _reduce_workflow_graph,
    _reduce_automation_workspace,
    _reduce_brain_state,
    *MODEL_REDUCERS,
    *TOOL_REDUCERS,
    *ARTIFACT_REDUCERS,
    *EXECUTION_EVENT_REDUCERS,
    _reduce_operation_saved,
    _reduce_operation_loaded,
    _reduce_journal_entry_appended,
    _reduce_world_model,
    _reduce_capability_library,
    _reduce_execution_library,
    _reduce_agent_pipeline_snapshot,
    _reduce_provider_registry,
    _reduce_workflow_library,
    _reduce_permission_snapshot,
)


class AppStateStore:
    """
    Holds current AppState; applies reducers on bus events.
    UI reads snapshots; never mutates services directly.
    """

    def __init__(self, bus: EventBus, reducers: tuple[Reducer, ...] | None = None) -> None:
        self._bus = bus
        self._reducers = reducers or _DEFAULT_REDUCERS
        self._lock = threading.RLock()
        self._state = AppState()
        self._listeners: list[Callable[[AppState], None]] = []
        self._unsubscribers: list[Callable[[], None]] = []
        for topic in APP_STATE_TOPICS:
            self._unsubscribers.append(bus.subscribe(topic, self._on_event))

    @property
    def snapshot(self) -> AppState:
        with self._lock:
            return self._state

    def subscribe(self, listener: Callable[[AppState], None]) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(listener)

        def unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return unsubscribe

    def _on_event(self, event: Event) -> None:
        listeners: list[Callable[[AppState], None]] = []
        new_state = self._state
        with self._lock:
            prior_state = self._state
            for reducer in self._reducers:
                new_state = reducer(new_state, event)
            if new_state != self._state:
                self._state = new_state
                notify_listeners = True
                if (
                    event.topic == SYSTEM_SNAPSHOT
                    and system_snapshot_metrics_only_delta(
                        prior_state.system_snapshot,
                        new_state.system_snapshot,
                    )
                ):
                    notify_listeners = False
                if notify_listeners:
                    listeners = list(self._listeners)

        if not listeners:
            return

        for listener in listeners:
            try:
                listener(new_state)
            except Exception as exc:
                logger.exception("AppState listener failed for topic=%s", event.topic)
                try:
                    self._bus.publish(
                        APP_ERROR,
                        {
                            "message": f"AppState listener failed: {exc}",
                            "topic": event.topic,
                        },
                        source="app_state",
                    )
                except Exception:
                    logger.exception("Failed to publish app.error for listener failure")

    def close(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
