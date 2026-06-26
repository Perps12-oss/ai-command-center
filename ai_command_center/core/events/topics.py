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
- **Workspace OS** (`ui.workspace_os.*`, `ui.inspector.*`): entity creation,
  resource launch, and inspector control.
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

CONVERSATION_UPDATED = "conversation.updated"
NOTES_INDEXED = "notes.indexed"

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
COMMAND_ROUTED = "command.routed"
UI_COMMAND = "ui.command"
UI_NAVIGATE = "ui.navigate"
UI_PALETTE_OPEN = "ui.palette_open"
UI_PALETTE_CLOSE = "ui.palette_close"
UI_CHAT_CANCEL = "ui.chat_cancel"
OVERLAY_SHOW = "overlay.show"
OVERLAY_HIDE = "overlay.hide"
OVERLAY_ANCHOR = "overlay.anchor"

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

SYSTEM_EVENTS = "system.events"
COMMAND_HISTORY = "command.history"

# Workspace OS UI topics (Track B - Phase 2)
UI_INSPECTOR_OPEN = "ui.inspector.open"
UI_INSPECTOR_CLOSE = "ui.inspector.close"
UI_CREATE_WORKSPACE = "ui.workspace_os.create_workspace"
UI_CREATE_CARD = "ui.workspace_os.create_card"
UI_CREATE_RESOURCE = "ui.workspace_os.create_resource"
UI_LAUNCH_RESOURCE = "ui.workspace_os.launch_resource"
UI_SEARCH_WORKSPACE_OS = "ui.workspace_os.search"


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
    "CONVERSATION_UPDATED",
    "NOTES_INDEXED",
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
    "COMMAND_ROUTED",
    "UI_COMMAND",
    "UI_NAVIGATE",
    "UI_PALETTE_OPEN",
    "UI_PALETTE_CLOSE",
    "UI_CHAT_CANCEL",
    "OVERLAY_SHOW",
    "OVERLAY_HIDE",
    "OVERLAY_ANCHOR",
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
    "SYSTEM_EVENTS",
    "COMMAND_HISTORY",
    "UI_INSPECTOR_OPEN",
    "UI_INSPECTOR_CLOSE",
    "UI_CREATE_WORKSPACE",
    "UI_CREATE_CARD",
    "UI_CREATE_RESOURCE",
    "UI_LAUNCH_RESOURCE",
    "UI_SEARCH_WORKSPACE_OS",
]
