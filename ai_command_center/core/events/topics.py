"""Canonical event topics used throughout the application.

This module is the single source of truth for all EventBus topics. Services,
UI, AppState reducers, and verification scripts must use these constants; no
hard-coded topic strings should exist elsewhere. Every topic is explicit and
versioned; wildcard subscriptions are restricted to debug/diagnostic code.

Topic categories:

- **Settings** (`settings.*`): settings mutation, snapshots, and change events.
- **Service lifecycle** (`service.*`): `service.started`, `service.ready`,
  `service.stopped`, `service.error`.
- **Chat** (`chat.*`): request, chunk, complete, cancel, error, export, and
  clipboard helpers.
- **Memory** (`memory.*`): remember, lookup, store, select, delete.
- **Notes** (`note.*`): select, search, create, index, context.
- **Plugins** (`plugin.*`): enable/disable, catalog, state changes, errors.
- **Tools** (`tool.*`): invoke, started, completed, failed, result, error.
- **System** (`system.*`): snapshot, events, telemetry.
- **Model** (`model.*`, `ollama.*`): selection and resolution.
- **Context** (`context.*`): context assembly and budget warnings.
- **Session** (`session.*`): conversation history persistence.
- **UI** (`ui.*`, `overlay.*`, `app.*`): user intent and overlay control.
- **Agent** (`agent.*`): spawn, task, pipeline lifecycle.
- **Capability runtime** (`capability.*`): ARI classification, dispatch, streaming.
"""

from __future__ import annotations

# Version marker for verification scripts and diagnostics.
TOPIC_VERSION = 1

SETTINGS_UPDATED = "settings.updated"
SETTINGS_SNAPSHOT = "settings.snapshot"
SETTINGS_CHANGED = "settings.changed"
SETTINGS_SET_REQUEST = "settings.set_request"

SERVICE_STARTED = "service.started"
SERVICE_READY = "service.ready"
SERVICE_STOPPED = "service.stopped"
SERVICE_ERROR = "service.error"
SERVICE_STATE_CHANGED = "service.state_changed"
SERVICE_RESTART_REQUEST = "service.restart_request"

CONVERSATION_UPDATED = "conversation.updated"
NOTES_INDEXED = "notes.indexed"

TOOL_REGISTERED = "tool.registered"
TOOL_STARTED = "tool.started"
TOOL_COMPLETED = "tool.completed"
TOOL_FAILED = "tool.failed"
TOOL_RESULT = "tool.result"
TOOL_ERROR = "tool.error"
TOOL_INVOKE = "tool.invoke"

TELEMETRY_EVENT = "telemetry.event"
TELEMETRY_EVENTS = TELEMETRY_EVENT
SYSTEM_SNAPSHOT = "system.snapshot"

APP_PHASE = "app.phase"
APP_ERROR = "app.error"
APP_WARNING = "app.warning"
BUS_HANDLER_ERROR = "bus.handler_error"
COMMAND_DEFERRED = "command.deferred"
UI_COMMAND = "ui.command"
UI_WORKSPACE_REQUIRED = "ui.workspace.required"
UI_NAVIGATE = "ui.navigate"
UI_PALETTE_OPEN = "ui.palette_open"
UI_PALETTE_CLOSE = "ui.palette_close"
UI_CHAT_CANCEL = "ui.chat_cancel"
UI_CHAT_NEW_SESSION = "ui.chat.new_session"
OVERLAY_SHOW = "overlay.show"
OVERLAY_HIDE = "overlay.hide"
OVERLAY_ANCHOR = "overlay.anchor"

# Global Inspector System — Design Item #2
UI_INSPECT_SELECT = "ui.inspect.select"
UI_INSPECT_CLEAR = "ui.inspect.clear"
UI_INSPECT_NAVIGATE = "ui.inspect.navigate"

CHAT_STARTED = "chat.started"
CHAT_CHUNK = "chat.chunk"
CHAT_COMPLETE = "chat.complete"
CHAT_CANCELLED = "chat.cancelled"
CHAT_ERROR = "chat.error"
CHAT_HISTORY_LOADED = "chat.history_loaded"
CHAT_REQUEST = "chat.request"
CHAT_EXPORT_REQUEST = "chat.export_request"
CHAT_EXPORT_RESULT = "chat.export_result"
CHAT_EXPORT_ERROR = "chat.export_error"

CLIPBOARD_REQUEST = "clipboard.request"
CLIPBOARD_CONTENT = "clipboard.content"

OLLAMA_STATUS = "ollama.status"
OPENAI_STATUS = "openai.status"
OLLAMA_MODEL_LOADED = "ollama.model_loaded"
OLLAMA_MODEL_UNLOADED = "ollama.model_unloaded"

MODEL_SELECTED = "model.selected"
MODEL_RESOLVE_REQUEST = "model.resolve.request"
MODEL_RESOLVE_RESULT = "model.resolve.result"

CONTEXT_REQUEST = "context.request"
CONTEXT_FRAGMENT = "context.fragment"
CONTEXT_SNAPSHOT_CREATED = "context.snapshot_created"
CONTEXT_OVER_BUDGET = "context.over_budget"
CONTEXT_TRIMMED = "context.trimmed"
CONTEXT_COMPLETE = "context.complete"

MEMORY_REMEMBER = "memory.remember"
MEMORY_SELECT = "memory.select"
MEMORY_LOOKUP_REQUEST = "memory.lookup.request"
MEMORY_LOOKUP_RESULT = "memory.lookup.result"
MEMORY_STORED = "memory.stored"
MEMORY_SELECTED = "memory.selected"
MEMORY_ERROR = "memory.error"
MEMORY_CLEARED = "memory.cleared"
MEMORY_CLEAR_SELECTION = "memory.clear_selection"
MEMORY_DELETE_REQUEST = "memory.delete_request"

SESSION_HISTORY_REQUEST = "session.history.request"
SESSION_HISTORY_RESULT = "session.history.result"
SESSION_UPDATE_REQUEST = "session.update.request"
SESSION_UPDATE_RESULT = "session.update.result"

NOTE_SELECT = "note.select"
NOTE_SELECTED = "note.selected"
NOTE_SEARCH_RESULTS = "note.search_results"
NOTE_CREATED = "note.created"
NOTE_ERROR = "note.error"
NOTE_INDEX_COMPLETE = "note.index_complete"
NOTE_INDEX_PROGRESS = "note.index_progress"
NOTE_CONTEXT_REQUEST = "note.context.request"
NOTE_CONTEXT_RESULT = "note.context.result"

PLUGIN_ENABLE_REQUEST = "plugin.enable_request"
PLUGIN_DISABLE_REQUEST = "plugin.disable_request"
PLUGIN_CATALOG = "plugin.catalog"
PLUGIN_STATE_CHANGED = "plugin.state_changed"
PLUGIN_ERROR = "plugin.error"

LLM_REQUEST = "llm.request"
LLM_CHUNK = "llm.chunk"
LLM_COMPLETE = "llm.complete"
LLM_ERROR = "llm.error"
LLM_CANCEL = "llm.cancel"

SYSTEM_EVENTS = "system.events"
COMMAND_HISTORY = "command.history"

# Workspace OS UI topics (Track B - Phase 2)
UI_INSPECTOR_OPEN = "ui.inspector.open"
UI_INSPECTOR_CLOSE = "ui.inspector.close"
UI_ORCHESTRATION_INSPECTOR_OPEN = "ui.orchestration_inspector.open"
UI_CREATE_WORKSPACE = "ui.workspace_os.create_workspace"
UI_CREATE_CARD = "ui.workspace_os.create_card"
UI_CREATE_RESOURCE = "ui.workspace_os.create_resource"
UI_LAUNCH_RESOURCE = "ui.workspace_os.launch_resource"
UI_OPEN_CHAT = "ui.workspace_os.open_chat"
UI_SELECT_WORKSPACE = "ui.workspace_os.select_workspace"
UI_SELECT_ENTITY = "ui.workspace_os.select_entity"
UI_SEARCH_WORKSPACE_OS = "ui.workspace_os.search"

# Workspace lifecycle (Program 3 — active workspace scope)
WORKSPACE_CREATED = "workspace.created"
WORKSPACE_ACTIVE = "workspace.active"
WORKSPACE_ACTIVATED = "workspace.activated"
WORKSPACE_DEACTIVATED = "workspace.deactivated"
WORKSPACE_LAYOUT_CHANGED = "workspace.layout.changed"
WORKSPACE_CONTEXT_REQUEST = "workspace.context.request"
WORKSPACE_CONTEXT_RESULT = "workspace.context.result"

# Agent framework (Track 7 — A0/A1)
AGENT_SPAWN_REQUEST = "agent.spawn.request"
AGENT_SPAWNED = "agent.spawned"
AGENT_TASK_REQUEST = "agent.task.request"
AGENT_TASK_COMPLETE = "agent.task.complete"
AGENT_TERMINATED = "agent.terminated"
AGENT_CANCEL_REQUEST = "agent.cancel.request"

# Agent orchestration pipeline (Track 7 — A4)
AGENT_PIPELINE_STARTED = "agent.pipeline.started"
AGENT_PIPELINE_STAGE = "agent.pipeline.stage"
AGENT_PIPELINE_PLANNED = "agent.pipeline.planned"
AGENT_PIPELINE_COMPLETE = "agent.pipeline.complete"

# Agent capability handoff — ExecutionAuthority owns plan creation (no TOOL_INVOKE).
AGENT_EXECUTION_REQUEST = "agent.execution.request"

# Capability runtime (Agent Runtime Interface — Invariant 13)
CAPABILITY_CLASSIFIED = "capability.classified"
CAPABILITY_DISPATCH = "capability.dispatch"
CAPABILITY_RUNTIME_REQUEST = "capability.runtime.request"
CAPABILITY_STREAM = "capability.stream"
CAPABILITY_COMPLETE = "capability.complete"
CAPABILITY_ERROR = "capability.error"
CAPABILITY_FALLBACK = "capability.fallback"
CAPABILITY_PROVIDERS_READY = "capability.providers.ready"
CAPABILITY_LIFECYCLE_SNAPSHOT = "capability.lifecycle.snapshot"
CAPABILITY_CATALOG_REQUEST = "capability.catalog.request"
CAPABILITY_CATALOG_RESULT = "capability.catalog.result"

# Planner layer (vNext L4 — goal to plan DAG, no execution)
PLAN_REQUEST = "plan.request"
PLAN_GENERATED = "plan.generated"
PLAN_FAILED = "plan.failed"

# Execution orchestrator (vNext L5 — approved plan execution with gates)
EXECUTION_RUN_REQUEST = "execution.run.request"
EXECUTION_RUN_STARTED = "execution.run.started"
EXECUTION_RUN_COMPLETE = "execution.run.complete"
EXECUTION_RUN_FAILED = "execution.run.failed"
EXECUTION_STEP_STARTED = "execution.step.started"
EXECUTION_STEP_AWAITING_APPROVAL = "execution.step.awaiting_approval"
EXECUTION_STEP_APPROVED = "execution.step.approved"
EXECUTION_STEP_COMPLETED = "execution.step.completed"
EXECUTION_STEP_FAILED = "execution.step.failed"

# Brain v1 goal scheduler (single-active-goal queue)
GOAL_SUBMIT_REQUEST = "goal.submit.request"
GOAL_SUBMITTED = "goal.submitted"
GOAL_ACTIVATED = "goal.activated"
GOAL_PAUSED = "goal.paused"
GOAL_RESUMED = "goal.resumed"
GOAL_CANCELLED = "goal.cancelled"
GOAL_COMPLETED = "goal.completed"
GOAL_FAILED = "goal.failed"
TASK_READY = "task.ready"
TASK_COMPLETED = "task.completed"
TASK_FAILED = "task.failed"

# Brain v1 observer framework
OBSERVATION_RECEIVED = "observation.received"
OBSERVATION_BATCH_RECEIVED = "observation.batch_received"
OBSERVATION_FAILED = "observation.failed"
OBSERVER_STARTED = "observer.started"
OBSERVER_STOPPED = "observer.stopped"
OBSERVER_ERROR = "observer.error"

# Brain v1 runtime safety gateway
RUNTIME_ACTION_REQUEST = "runtime.action.request"
RUNTIME_ACTION_STARTED = "runtime.action_started"
RUNTIME_APPROVAL_REQUESTED = "runtime.approval_requested"
RUNTIME_APPROVAL_DECIDED = "runtime.approval_decided"
RUNTIME_ACTION_COMPLETED = "runtime.action_completed"
RUNTIME_ACTION_FAILED = "runtime.action_failed"
RUNTIME_ACTION_DENIED = "runtime.action_denied"
RUNTIME_WORLD_MODEL_APPLY_REQUESTED = "runtime.world_model_apply_requested"
RUNTIME_WORLD_MODEL_APPLY_COMPLETED = "runtime.world_model_apply_completed"

# Brain v1 kernel state machine
KERNEL_STATE_CHANGED = "kernel.state_changed"
KERNEL_TRANSITION_REJECTED = "kernel.transition_rejected"
KERNEL_RECOVERY_STARTED = "kernel.recovery_started"
KERNEL_RECOVERY_COMPLETED = "kernel.recovery_completed"
KERNEL_TIMEOUT = "kernel.timeout"

# External integrations (vNext Phase E — MCP/email/calendar via ARI)
EXTERNAL_CAPABILITY_REGISTER = "external.capability.register"
EXTERNAL_CAPABILITY_UNREGISTER = "external.capability.unregister"
EXTERNAL_CAPABILITY_REGISTERED = "external.capability.registered"
EXTERNAL_CAPABILITY_CATALOG_UPDATED = "external.capability.catalog_updated"
EXTERNAL_PROVIDER_DISCOVERED = "external.provider.discovered"

# Execution authority (runtime-first intake for typed UI_COMMAND)
EXECUTION_AUTHORITY_DECISION = "execution.authority.decision"
LLM_STEP_REQUEST = "llm.step.request"

# Truth-bound orchestration (deterministic intents, receipts, truth boundary)
ORCHESTRATION_INTENT_CLASSIFIED = "orchestration.intent.classified"
ORCHESTRATION_ROUTING_COMPLETED = "orchestration.routing.completed"
ORCHESTRATION_PROVIDER_SELECTED = "orchestration.provider.selected"
ORCHESTRATION_RECEIPT = "orchestration.receipt"
ORCHESTRATION_TRUTH_VALIDATED = "orchestration.truth.validated"
ORCHESTRATION_RUN_SNAPSHOT = "orchestration.run.snapshot"
ORCHESTRATION_PROVIDER_HEALTH = "orchestration.provider.health"

# Permission gate (Track 7 — supervised agent pre-flight)
PERMISSION_CHECK_REQUEST = "permission.check.request"
PERMISSION_CHECK_RESULT = "permission.check.result"

# Workflow engine (Track 8 — W0/W1)
WORKFLOW_START = "workflow.start"
WORKFLOW_STARTED = "workflow.started"
WORKFLOW_STEP_STARTED = "workflow.step.started"
WORKFLOW_STEP_COMPLETED = "workflow.step.completed"
WORKFLOW_COMPLETED = "workflow.completed"
WORKFLOW_FAILED = "workflow.failed"
WORKFLOW_RUNS_LOADED = "workflow.runs.loaded"
# Definition provider → ExecutionAuthority intake (never TOOL_INVOKE).
WORKFLOW_EXECUTION_REQUEST = "workflow.execution.request"

# Entity lifecycle (Workspace OS / entity service)
ENTITY_CREATED = "entity.created"
ENTITY_UPDATED = "entity.updated"
ENTITY_DELETED = "entity.deleted"
ENTITY_RELATIONSHIPS_CHANGED = "entity.relationships.changed"

# Entity bus request/result (Program 3 W3 — bus-native Workspace OS)
ENTITY_CREATE_REQUEST = "entity.create.request"
ENTITY_CREATE_RESULT = "entity.create.result"
ENTITY_SEARCH_REQUEST = "entity.search.request"
ENTITY_SEARCH_RESULT = "entity.search.result"
ENTITY_CONTEXT_REQUEST = "entity.context.request"
ENTITY_CONTEXT_RESULT = "entity.context.result"
RELATIONSHIP_CREATE_REQUEST = "relationship.create.request"
RELATIONSHIP_CREATE_RESULT = "relationship.create.result"
WORKSPACE_CREATE_REQUEST = "workspace.create.request"
WORKSPACE_CREATE_RESULT = "workspace.create.result"
WORKSPACE_ADD_ENTITY_REQUEST = "workspace.add_entity.request"
WORKSPACE_ADD_ENTITY_RESULT = "workspace.add_entity.result"
ACTION_INVOKE_REQUEST = "action.invoke.request"
ACTION_INVOKE_RESULT = "action.invoke.result"
TIMELINE_RECORD_REQUEST = "timeline.record.request"
TIMELINE_RECORD_RESULT = "timeline.record.result"
SEARCH_RESULTS = "search.results"

# Execution query (UI Refurbishment P3 Slice 1b — Inspector docked panel)
EXECUTION_QUERY_REQUEST = "execution.query.request"
EXECUTION_QUERY_RESULT = "execution.query.result"

# Artifact catalog (ACC UI Refurbishment PR 6)
ARTIFACT_CREATED = "artifact.created"
ARTIFACT_UPDATED = "artifact.updated"
ARTIFACTS_LOADED = "artifacts.loaded"

# Execution timeline stream (ACC UI Refurbishment PR 8)
EXECUTION_EVENT_APPENDED = "execution.event.appended"
EXECUTION_EVENTS_LOADED = "execution.events.loaded"
EXECUTION_RUNS_LOADED = "execution.runs.loaded"

# Execution timeline UI (ACC UI Refurbishment PR 9)
UI_EXECUTION_TIMELINE_SCRUB = "ui.execution.timeline.scrub"

# Workflow graph workspace (ACC UI Refurbishment PR 12–13)
UI_WORKFLOW_NODE_SELECT = "ui.workflow.node.select"
UI_WORKFLOW_NODE_MOVE = "ui.workflow.node.move"
UI_WORKFLOW_RUN = "ui.workflow.run"

# Automation workspace (ACC UI Refurbishment PR 14–15)
UI_AUTOMATION_RUN = "ui.automation.run"
UI_AUTOMATION_SELECT = "ui.automation.select"
UI_AUTOMATION_SCHEDULE_TOGGLE = "ui.automation.schedule.toggle"

# Timeline undo (workspace OS)
TIMELINE_UNDO_REQUEST = "timeline.undo.request"
TIMELINE_UNDO_RESULT = "timeline.undo.result"

# UI artifact actions (UI Refurbishment P3 Slice 1b — artifact viewer bus integration)
UI_ARTIFACT_ACTION = "ui.artifact.action"
ARTIFACT_PREVIEW = "artifact.preview"
ARTIFACT_EXPORT = "artifact.export"
ARTIFACT_DELETE = "artifact.delete"

# Workflow graph edge management (UI Refurbishment P3 Slice 1b)
UI_WORKFLOW_EDGE_CREATE = "ui.workflow.edge.create"
UI_WORKFLOW_EDGE_DELETE = "ui.workflow.edge.delete"

# Operations Library and Focus Navigation (Blueprint Phase 0)
# FOCUS_SELECTED payload: {focus_id: str, focus_type: str, correlation_id: str}
FOCUS_SELECTED = "focus.selected"
# FOCUS_RESOLUTION_FAILED payload: {focus_id: str, reason: str}
FOCUS_RESOLUTION_FAILED = "focus.resolution_failed"
# OPERATION_LOAD_REQUEST payload: {correlation_id: str}
OPERATION_LOAD_REQUEST = "operation.load_request"
# OPERATION_LOADED payload: {correlation_id: str, snapshot: dict}
OPERATION_LOADED = "operation.loaded"
# OPERATION_SAVED payload: {correlation_id: str, goal_id: str, goal_title: str, goal_status: str}
OPERATION_SAVED = "operation.saved"
# OPERATION_ARCHIVED payload: {correlation_id: str, frozen_at: float}
OPERATION_ARCHIVED = "operation.archived"
# LAYOUT_PREFERENCE_CHANGED payload: {layout_key: str, value: dict}
LAYOUT_PREFERENCE_CHANGED = "layout.preference_changed"
# JOURNAL_ENTRY_APPENDED payload: {correlation_id: str, kind: str, summary: str, object_id: str, object_type: str, timestamp: float}
JOURNAL_ENTRY_APPENDED = "journal.entry_appended"
# COMPOSITION_RECIPE_RESOLVED payload: {focus_id: str, recipe: dict, panels: list}
COMPOSITION_RECIPE_RESOLVED = "composition.recipe_resolved"

# World Model UI (Phase 10 — P3)
WORLD_MODEL_NODE_SELECTED = "world_model.node.selected"
WORLD_MODEL_NODE_DESELECTED = "world_model.node.deselected"
WORLD_MODEL_GRAPH_REFRESHED = "world_model.graph.refreshed"
WORLD_MODEL_MUTATION_APPLIED = "world_model.mutation.applied"
WORLD_MODEL_EXPLORER_OPEN = "world_model.explorer.open"
WORLD_MODEL_DEPENDENCY_INSPECT = "world_model.dependency.inspect"

# State Authority — pre-decision World Model projection
STATE_CONTEXT_BUILT = "state.context.built"
STATE_CONTEXT_REQUEST = "state.context.request"
STATE_CONTEXT_RESULT = "state.context.result"

# Cross-Workspace Federation (Phase 10 — P4)
FEDERATION_WORKSPACE_REGISTERED = "federation.workspace.registered"
FEDERATION_WORKSPACE_UNREGISTERED = "federation.workspace.unregistered"
FEDERATION_QUERY_REQUEST = "federation.query.request"
FEDERATION_QUERY_RESULT = "federation.query.result"
FEDERATION_SYNC_STARTED = "federation.sync.started"
FEDERATION_SYNC_COMPLETED = "federation.sync.completed"
FEDERATION_CONFLICT_DETECTED = "federation.conflict.detected"


__all__ = [
    "TOPIC_VERSION",
    "SETTINGS_UPDATED",
    "SETTINGS_SNAPSHOT",
    "SETTINGS_CHANGED",
    "SETTINGS_SET_REQUEST",
    "SERVICE_STARTED",
    "SERVICE_READY",
    "SERVICE_STOPPED",
    "SERVICE_ERROR",
    "SERVICE_STATE_CHANGED",
    "SERVICE_RESTART_REQUEST",
    "CONVERSATION_UPDATED",
    "NOTES_INDEXED",
    "TOOL_REGISTERED",
    "TOOL_STARTED",
    "TOOL_COMPLETED",
    "TOOL_FAILED",
    "TOOL_RESULT",
    "TOOL_ERROR",
    "TOOL_INVOKE",
    "TELEMETRY_EVENT",
    "TELEMETRY_EVENTS",
    "SYSTEM_SNAPSHOT",
    "APP_PHASE",
    "APP_ERROR",
    "APP_WARNING",
    "BUS_HANDLER_ERROR",
    "COMMAND_DEFERRED",
    "UI_COMMAND",
    "UI_WORKSPACE_REQUIRED",
    "UI_NAVIGATE",
    "UI_PALETTE_OPEN",
    "UI_PALETTE_CLOSE",
    "UI_CHAT_CANCEL",
    "UI_CHAT_NEW_SESSION",
    "OVERLAY_SHOW",
    "OVERLAY_HIDE",
    "OVERLAY_ANCHOR",
    "UI_INSPECT_SELECT",
    "UI_INSPECT_CLEAR",
    "UI_INSPECT_NAVIGATE",
    "CHAT_STARTED",
    "CHAT_CHUNK",
    "CHAT_COMPLETE",
    "CHAT_CANCELLED",
    "CHAT_ERROR",
    "CHAT_HISTORY_LOADED",
    "CHAT_REQUEST",
    "CHAT_EXPORT_REQUEST",
    "CHAT_EXPORT_RESULT",
    "CHAT_EXPORT_ERROR",
    "CLIPBOARD_REQUEST",
    "CLIPBOARD_CONTENT",
    "OLLAMA_STATUS",
    "OPENAI_STATUS",
    "OLLAMA_MODEL_LOADED",
    "OLLAMA_MODEL_UNLOADED",
    "MODEL_SELECTED",
    "MODEL_RESOLVE_REQUEST",
    "MODEL_RESOLVE_RESULT",
    "CONTEXT_REQUEST",
    "CONTEXT_FRAGMENT",
    "CONTEXT_SNAPSHOT_CREATED",
    "CONTEXT_OVER_BUDGET",
    "CONTEXT_TRIMMED",
    "CONTEXT_COMPLETE",
    "MEMORY_REMEMBER",
    "MEMORY_SELECT",
    "MEMORY_LOOKUP_REQUEST",
    "MEMORY_LOOKUP_RESULT",
    "MEMORY_STORED",
    "MEMORY_SELECTED",
    "MEMORY_ERROR",
    "MEMORY_CLEARED",
    "MEMORY_CLEAR_SELECTION",
    "MEMORY_DELETE_REQUEST",
    "SESSION_HISTORY_REQUEST",
    "SESSION_HISTORY_RESULT",
    "SESSION_UPDATE_REQUEST",
    "SESSION_UPDATE_RESULT",
    "NOTE_SELECT",
    "NOTE_SELECTED",
    "NOTE_SEARCH_RESULTS",
    "NOTE_CREATED",
    "NOTE_ERROR",
    "NOTE_INDEX_COMPLETE",
    "NOTE_INDEX_PROGRESS",
    "NOTE_CONTEXT_REQUEST",
    "NOTE_CONTEXT_RESULT",
    "PLUGIN_ENABLE_REQUEST",
    "PLUGIN_DISABLE_REQUEST",
    "PLUGIN_CATALOG",
    "PLUGIN_STATE_CHANGED",
    "PLUGIN_ERROR",
    "LLM_REQUEST",
    "LLM_CHUNK",
    "LLM_COMPLETE",
    "LLM_ERROR",
    "LLM_CANCEL",
    "SYSTEM_EVENTS",
    "COMMAND_HISTORY",
    "UI_INSPECTOR_OPEN",
    "UI_INSPECTOR_CLOSE",
    "UI_ORCHESTRATION_INSPECTOR_OPEN",
    "UI_CREATE_WORKSPACE",
    "UI_CREATE_CARD",
    "UI_CREATE_RESOURCE",
    "UI_LAUNCH_RESOURCE",
    "UI_OPEN_CHAT",
    "UI_SELECT_WORKSPACE",
    "UI_SELECT_ENTITY",
    "UI_SEARCH_WORKSPACE_OS",
    "WORKSPACE_CREATED",
    "WORKSPACE_ACTIVE",
    "WORKSPACE_ACTIVATED",
    "WORKSPACE_DEACTIVATED",
    "WORKSPACE_LAYOUT_CHANGED",
    "WORKSPACE_CONTEXT_REQUEST",
    "WORKSPACE_CONTEXT_RESULT",
    "AGENT_SPAWN_REQUEST",
    "AGENT_SPAWNED",
    "AGENT_TASK_REQUEST",
    "AGENT_TASK_COMPLETE",
    "AGENT_TERMINATED",
    "AGENT_CANCEL_REQUEST",
    "AGENT_PIPELINE_STARTED",
    "AGENT_PIPELINE_STAGE",
    "AGENT_PIPELINE_PLANNED",
    "AGENT_PIPELINE_COMPLETE",
    "AGENT_EXECUTION_REQUEST",
    "CAPABILITY_CLASSIFIED",
    "CAPABILITY_DISPATCH",
    "CAPABILITY_RUNTIME_REQUEST",
    "CAPABILITY_STREAM",
    "CAPABILITY_COMPLETE",
    "CAPABILITY_ERROR",
    "CAPABILITY_FALLBACK",
    "CAPABILITY_PROVIDERS_READY",
    "CAPABILITY_LIFECYCLE_SNAPSHOT",
    "CAPABILITY_CATALOG_REQUEST",
    "CAPABILITY_CATALOG_RESULT",
    "PLAN_REQUEST",
    "PLAN_GENERATED",
    "PLAN_FAILED",
    "EXECUTION_RUN_REQUEST",
    "EXECUTION_RUN_STARTED",
    "EXECUTION_RUN_COMPLETE",
    "EXECUTION_RUN_FAILED",
    "EXECUTION_STEP_STARTED",
    "EXECUTION_STEP_AWAITING_APPROVAL",
    "EXECUTION_STEP_APPROVED",
    "EXECUTION_STEP_COMPLETED",
    "EXECUTION_STEP_FAILED",
    "GOAL_SUBMIT_REQUEST",
    "GOAL_SUBMITTED",
    "GOAL_ACTIVATED",
    "GOAL_PAUSED",
    "GOAL_RESUMED",
    "GOAL_CANCELLED",
    "GOAL_COMPLETED",
    "GOAL_FAILED",
    "TASK_READY",
    "TASK_COMPLETED",
    "TASK_FAILED",
    "OBSERVATION_RECEIVED",
    "OBSERVATION_BATCH_RECEIVED",
    "OBSERVATION_FAILED",
    "OBSERVER_STARTED",
    "OBSERVER_STOPPED",
    "OBSERVER_ERROR",
    "RUNTIME_ACTION_REQUEST",
    "RUNTIME_ACTION_STARTED",
    "RUNTIME_APPROVAL_REQUESTED",
    "RUNTIME_APPROVAL_DECIDED",
    "RUNTIME_ACTION_COMPLETED",
    "RUNTIME_ACTION_FAILED",
    "RUNTIME_ACTION_DENIED",
    "RUNTIME_WORLD_MODEL_APPLY_REQUESTED",
    "RUNTIME_WORLD_MODEL_APPLY_COMPLETED",
    "KERNEL_STATE_CHANGED",
    "KERNEL_TRANSITION_REJECTED",
    "KERNEL_RECOVERY_STARTED",
    "KERNEL_RECOVERY_COMPLETED",
    "KERNEL_TIMEOUT",
    "EXTERNAL_CAPABILITY_REGISTER",
    "EXTERNAL_CAPABILITY_UNREGISTER",
    "EXTERNAL_CAPABILITY_REGISTERED",
    "EXTERNAL_CAPABILITY_CATALOG_UPDATED",
    "EXTERNAL_PROVIDER_DISCOVERED",
    "EXECUTION_AUTHORITY_DECISION",
    "LLM_STEP_REQUEST",
    "ORCHESTRATION_INTENT_CLASSIFIED",
    "ORCHESTRATION_ROUTING_COMPLETED",
    "ORCHESTRATION_PROVIDER_SELECTED",
    "ORCHESTRATION_RECEIPT",
    "ORCHESTRATION_TRUTH_VALIDATED",
    "ORCHESTRATION_RUN_SNAPSHOT",
    "ORCHESTRATION_PROVIDER_HEALTH",
    "PERMISSION_CHECK_REQUEST",
    "PERMISSION_CHECK_RESULT",
    "WORKFLOW_START",
    "WORKFLOW_STARTED",
    "WORKFLOW_EXECUTION_REQUEST",
    "WORKFLOW_STEP_STARTED",
    "WORKFLOW_STEP_COMPLETED",
    "WORKFLOW_COMPLETED",
    "WORKFLOW_FAILED",
    "WORKFLOW_RUNS_LOADED",
    "ENTITY_CREATED",
    "ENTITY_UPDATED",
    "ENTITY_DELETED",
    "ENTITY_RELATIONSHIPS_CHANGED",
    "ENTITY_CREATE_REQUEST",
    "ENTITY_CREATE_RESULT",
    "ENTITY_SEARCH_REQUEST",
    "ENTITY_SEARCH_RESULT",
    "ENTITY_CONTEXT_REQUEST",
    "ENTITY_CONTEXT_RESULT",
    "RELATIONSHIP_CREATE_REQUEST",
    "RELATIONSHIP_CREATE_RESULT",
    "WORKSPACE_CREATE_REQUEST",
    "WORKSPACE_CREATE_RESULT",
    "WORKSPACE_ADD_ENTITY_REQUEST",
    "WORKSPACE_ADD_ENTITY_RESULT",
    "ACTION_INVOKE_REQUEST",
    "ACTION_INVOKE_RESULT",
    "TIMELINE_RECORD_REQUEST",
    "TIMELINE_RECORD_RESULT",
    "SEARCH_RESULTS",
    "EXECUTION_QUERY_REQUEST",
    "EXECUTION_QUERY_RESULT",
    "ARTIFACT_CREATED",
    "ARTIFACT_UPDATED",
    "ARTIFACTS_LOADED",
    "EXECUTION_EVENT_APPENDED",
    "EXECUTION_EVENTS_LOADED",
    "EXECUTION_RUNS_LOADED",
    "UI_EXECUTION_TIMELINE_SCRUB",
    "UI_WORKFLOW_NODE_SELECT",
    "UI_WORKFLOW_NODE_MOVE",
    "UI_WORKFLOW_RUN",
    "UI_AUTOMATION_RUN",
    "UI_AUTOMATION_SELECT",
    "UI_AUTOMATION_SCHEDULE_TOGGLE",
    "TIMELINE_UNDO_REQUEST",
    "TIMELINE_UNDO_RESULT",
    "UI_ARTIFACT_ACTION",
    "ARTIFACT_PREVIEW",
    "ARTIFACT_EXPORT",
    "ARTIFACT_DELETE",
    "UI_WORKFLOW_EDGE_CREATE",
    "UI_WORKFLOW_EDGE_DELETE",
    "FOCUS_SELECTED",
    "FOCUS_RESOLUTION_FAILED",
    "OPERATION_LOAD_REQUEST",
    "OPERATION_LOADED",
    "OPERATION_SAVED",
    "OPERATION_ARCHIVED",
    "LAYOUT_PREFERENCE_CHANGED",
    "JOURNAL_ENTRY_APPENDED",
    "COMPOSITION_RECIPE_RESOLVED",
    "WORLD_MODEL_NODE_SELECTED",
    "WORLD_MODEL_NODE_DESELECTED",
    "WORLD_MODEL_GRAPH_REFRESHED",
    "WORLD_MODEL_MUTATION_APPLIED",
    "WORLD_MODEL_EXPLORER_OPEN",
    "WORLD_MODEL_DEPENDENCY_INSPECT",
    "STATE_CONTEXT_BUILT",
    "STATE_CONTEXT_REQUEST",
    "STATE_CONTEXT_RESULT",
    "FEDERATION_WORKSPACE_REGISTERED",
    "FEDERATION_WORKSPACE_UNREGISTERED",
    "FEDERATION_QUERY_REQUEST",
    "FEDERATION_QUERY_RESULT",
    "FEDERATION_SYNC_STARTED",
    "FEDERATION_SYNC_COMPLETED",
    "FEDERATION_CONFLICT_DETECTED",
]
