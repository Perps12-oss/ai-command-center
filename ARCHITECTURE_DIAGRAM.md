# AI Command Center - Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI Command Center                                   │
│                    Windows ARM64 Desktop Application                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Layer Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                               UI Layer                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ CommandPalette│  │  System Tray │  │   Hotkey     │  │   Views      │    │
│  │     App       │  │  Controller  │  │  Manager     │  │ (Chat/Notes) │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                  │                  │                  │            │
│         └──────────────────┴──────────────────┴──────────────────┘            │
│                                    │                                          │
│                          ┌─────────▼─────────┐                                │
│                          │   UIController    │                                │
│                          │ (bus, state_store) │                                │
│                          └─────────┬─────────┘                                │
└────────────────────────────────────┼──────────────────────────────────────────┘
                                     │
                                     │ EventBus (publish intents)
                                     │
┌────────────────────────────────────▼──────────────────────────────────────────┐
│                           AppState Layer                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         AppStateStore                                  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │  │
│  │  │   Settings   │  │   Services   │  │    Chat      │  │  System   │ │  │
│  │  │  Snapshot    │  │  Snapshot    │  │   Status     │  │ Snapshot  │ │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘ │  │
│  │                                                                          │  │
│  │  Reducers: _reduce_settings, _reduce_service_state, _reduce_chat...   │  │
│  └──────────────────────────────────────┬───────────────────────────────────┘  │
│                                         │ (subscribe to events)                  │
└─────────────────────────────────────────┼──────────────────────────────────────┘
                                           │
                                           │ EventBus (subscribe topics)
                                           │
┌──────────────────────────────────────────▼─────────────────────────────────────┐
│                           Service Layer                                        │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │                        ServiceManager                                     │ │
│  │  (load_all, hibernate_all, shutdown)                                     │ │
│  └──────────────────────────────────────┬───────────────────────────────────┘ │
│                                           │                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───▼────────────┐  ┌──────────────┐      │
│  │   Settings   │  │   Ollama     │  │  ChatHandler  │  │   Obsidian   │      │
│  │   Service    │  │   Service    │  │   Service     │  │   Service    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │                 │               │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐      │
│  │  Command     │  │  Tool        │  │  Memory      │  │  Plugin      │      │
│  │  Router      │  │  Executor    │  │  Graph       │  │  Registry    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                                              │
│  All services extend BaseService with lifecycle:                             │
│  STOPPED → STARTING → IDLE → ACTIVE → READY                                  │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       │ EventBus (publish events)
                                       │
┌──────────────────────────────────────▼───────────────────────────────────────┐
│                           Repository Layer                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Settings   │  │ Conversation │  │    Note      │  │   Memory     │     │
│  │  Repository  │  │  Repository  │  │  Repository  │  │  Repository  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │                 │              │
│         └─────────────────┴─────────────────┴─────────────────┘              │
│                                    │                                          │
│                          ┌─────────▼─────────┐                                │
│                          │   SQLite (app.db) │                                │
│                          │  %APPDATA%\AICommandCenter                       │
│                          └───────────────────┘                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagrams

### 1. Application Startup Flow

```
main.py
  │
  ├─→ is_arm64() check
  ├─→ validate_hotkey()
  │
  ├─→ create_application()
  │     │
  │     ├─→ init_database() → SQLite connection
  │     ├─→ EventBus(debug_mode=False)
  │     ├─→ AppStateStore(bus)
  │     ├─→ ServiceManager(bus)
  │     │
  │     ├─→ Create repositories (Settings, Note, Memory, Conversation, Telemetry)
  │     ├─→ Create services (injected with repos + bus)
  │     │     ├─→ SettingsService
  │     │     ├─→ OllamaHttpService
  │     │     ├─→ ObsidianService
  │     │     ├─→ ChatHandlerService
  │     │     ├─→ ToolRegistryService
  │     │     ├─→ ToolExecutorService
  │     │     ├─→ MemoryGraphService
  │     │     ├─→ PluginRegistryService
  │     │     ├─→ TelemetryService
  │     │     └─→ SystemMonitorService
  │     │
  │     └─→ Return ApplicationCore(bus, state_store, services, db)
  │
  ├─→ core.startup()
  │     ├─→ publish "app.phase": "starting"
  │     ├─→ services.load_all() → all services start()
  │     ├─→ SystemSnapshotBuilder.publish()
  │     └─→ publish "app.phase": "ready"
  │
  ├─→ CommandPaletteApp(bus, state_store)
  │     ├─→ UIController(bus, state_store)
  │     ├─→ Subscribe to EventBus topics
  │     ├─→ Initialize views (Chat, Notes, Settings, etc.)
  │     └─→ MotionScheduler + BackgroundController
  │
  ├─→ TrayController(on_open, on_exit)
  ├─→ register_hotkey("alt+space", toggle_palette)
  │
  └─→ app.mainloop()
```

### 2. Command Execution Flow

```
User types command in UI
  │
  ├─→ UI publishes "ui.command" {text: "..."}
  │
  ├─→ CommandRouterService receives
  │     │
  │     ├─→ Parse intent (chat | shell | note_search | note_new | navigate)
  │     │
  │     └─→ Publish "command.routed" {text, intent, args}
  │
  ├─→ AppState reducer updates last_command, last_command_intent
  │
  └─→ Intent-specific handler:
        │
        ├─→ CHAT: ChatHandlerService
        │     │
        │     ├─→ ContextManager.build_context(query, notes, clipboard, history)
        │     │     ├─→ Token budgeting (70% of max)
        │     │     ├─→ Priority ordering (query > clipboard > notes > history)
        │     │     └─→ Return ContextBundle(prompt, sources, token_estimate)
        │     │
        │     ├─→ ModelRouterService.resolve() → model.selected
        │     │
        │     ├─→ OllamaHttpService.chat(prompt, model)
        │     │     ├─→ Publish "chat.started" {request_id}
        │     │     ├─→ Stream responses → "chat.chunk" events
        │     │     └─→ Publish "chat.complete" {text, request_id}
        │     │
        │     └─→ SessionService stores conversation
        │
        ├─→ SHELL: ShellToolService
        │     │
        │     ├─→ Publish "tool.invoke" {tool: "shell", command}
        │     ├─→ ToolExecutorService executes
        │     └─→ Publish "tool.result" {output, exit_code}
        │
        ├─→ NOTE_SEARCH: ObsidianService
        │     │
        │     ├─→ Search vault
        │     └─→ Publish "note.search_results" {notes}
        │
        └─→ NOTE_NEW: ObsidianService
              │
              ├─→ Create note file
              └─→ Publish "note.created" {path}
```

### 3. Settings Update Flow

```
User changes setting in UI
  │
  ├─→ UI publishes "settings.set_request" {key: "theme", value: "light"}
  │
  ├─→ SettingsService receives
  │     │
  │     ├─→ Validate value (bool, int, str, Path, Enum)
  │     ├─→ SettingsRepository.update(key, value) → SQLite
  │     │
  │     ├─→ Publish "settings.changed" {key, value}
  │     └─→ Publish "settings.snapshot" {full_settings_payload}
  │
  ├─→ AppState reducer:
  │     │
  │     ├─→ _reduce_settings_changed() → increment settings_version
  │     └─→ _reduce_settings_snapshot() → update settings field
  │
  └─→ UI re-renders from new AppState.snapshot.settings
```

### 4. Service State Flow

```
ServiceManager.load_all()
  │
  ├─→ For each service: service.start()
  │     │
  │     ├─→ _set_state(STARTING)
  │     ├─→ _on_load() → service-specific initialization
  │     ├─→ _set_state(IDLE)
  │     ├─→ _on_activate()
  │     ├─→ _set_state(ACTIVE)
  │     ├─→ _set_state(READY)
  │     │
  │     ├─→ Publish "service.started" {service: name}
  │     ├─→ Publish "service.ready" {service: name}
  │     └─→ Publish "service.state_changed" {name, state, detail}
  │
  └─→ AppState reducer _reduce_service_state()
        │
        └─→ Update AppState.services tuple with ServiceSnapshot
```

### 5. Context Building Flow

```
ChatHandlerService prepares AI request
  │
  ├─→ ContextManager.build_context(
  │     │     query,
  │     │     clipboard=None,
  │     │     notes=[...],
  │     │     conversation_history=[...],
  │     │     graph_snippets=[...]
  │     │ )
  │     │
  │     ├─→ Calculate budget: max_tokens * 0.70
  │     │
  │     ├─→ Compress conversation history if over budget
  │     │     └─→ Keep last 4 turns, summarize earlier
  │     │
  │     ├─→ Build sections with priority:
  │     │     0: conversation_summary
  │     │     1: conversation_history
  │     │     2: memory_graph snippets
  │     │     3: notes
  │     │     4: clipboard (if not intent-driven)
  │     │     5: user_query (always included)
  │     │
  │     ├─→ Sort by priority, fit within budget
  │     │     └─→ Trim lower-priority sections if needed
  │     │
  │     └─→ Return ContextBundle:
  │           ├─→ prompt: assembled text
  │           ├─→ sources: tuple of included section names
  │           └─→ token_estimate: total tokens
  │
  └─→ Publish "context.snapshot_created" {sources, context_size_tokens}
```

## Key Architectural Rules

### 1. Ownership Flow (Constitutional Invariant 1)
```
UI → AppState → EventBus → Services → Repositories → Storage
```
**No shortcut paths permitted.**

### 2. UI Isolation (Constitutional Invariant 2)
UI may **only**:
- Read from `AppStateStore.snapshot`
- Subscribe to `AppState` changes
- Publish intents to `EventBus`

UI may **never**:
- Access repositories directly
- Access SQLite directly
- Call services directly
- Access settings files directly

### 3. Repository Access Policy
**Only `ApplicationCore` (via `create_application()`) may construct repositories.**

| Layer | May access repositories? |
|-------|--------------------------|
| ApplicationCore | Yes - composition root only |
| Services | Yes - injected at registration |
| UI | **Never** |
| Scripts/tests | Prefer EventBus; debug-mode taps allowed |

### 4. State Ownership

**Operational State** (lives in services):
- Service lifecycle states (STOPPED, STARTING, READY, ACTIVE, ERROR)
- Runtime service process state
- Source of truth: `BaseService._state`
- UI visibility: mirrored via `service.state_changed` events

**Presentation State** (lives in AppState):
- UI-consumable snapshots
- Settings snapshot, service status, chat status
- Source of truth: `AppStateStore` reducers only
- Never written directly by services

### 5. EventBus Governance

**Wildcard subscriptions forbidden** in production code:
- ❌ `bus.subscribe_all(handler)`
- ❌ `bus.subscribe("*", handler)`

Allowed:
- ✅ Explicit topic subscriptions
- ✅ `EventBus(debug_mode=True)` for diagnostics/verification scripts

### 6. Context Pipeline (Constitutional Invariant 6)

**Every AI request must pass through ContextManager:**
```
User Query → ContextManager.build_context() → ContextBundle → OllamaService
```

ContextManager responsibilities:
- Token budgeting (70% fill ratio)
- Priority-based context assembly
- Conversation history compression
- No Ollama calls, no embeddings, no vectors

## Event Topics (Canonical Registry)

| Topic | Producer | Consumers | Purpose |
|-------|----------|-----------|---------|
| `settings.updated` | SettingsService | AppState, UI | Incremental setting change |
| `settings.snapshot` | SettingsService | AppState, UI | Full settings projection |
| `service.state_changed` | BaseService | AppState | Service lifecycle updates |
| `command.routed` | CommandRouterService | Intent handlers | Parsed command with intent |
| `chat.started` | ChatHandlerService | AppState, UI | Begin chat request |
| `chat.chunk` | OllamaHttpService | UI | Streaming response |
| `chat.complete` | ChatHandlerService | AppState, UI | Chat finished |
| `tool.invoke` | ShellToolService | ToolExecutor | Execute tool |
| `tool.result` | ToolExecutorService | UI, telemetry | Tool output |
| `context.snapshot_created` | ContextManager | AppState | Context assembly complete |
| `system.snapshot` | SystemSnapshotBuilder | AppState | System health snapshot |
| `app.phase` | Application | All | Application lifecycle |

## Module Structure

```
ai_command_center/
├── application.py              # Composition root
├── core/
│   ├── event_bus.py           # Thread-safe pub/sub
│   ├── app_state.py           # Immutable state + reducers
│   ├── service_manager.py     # Service lifecycle orchestration
│   ├── context_manager.py     # AI context budget manager
│   ├── settings/              # Settings schema + service
│   ├── state/                 # State builders
│   └── events/
│       └── topics.py         # Canonical topic registry
├── services/
│   ├── base.py               # BaseService lifecycle contract
│   ├── settings_service.py   # Settings management
│   ├── ollama_http_service.py # Ollama HTTP client
│   ├── chat_handler_service.py # Chat orchestration
│   ├── command_router_service.py # Intent routing
│   ├── obsidian_service.py   # Obsidian vault integration
│   ├── tool_executor_service.py # Tool execution
│   ├── memory_graph_service.py # Memory graph
│   └── telemetry_service.py  # Passive telemetry
├── repositories/
│   ├── settings_repository.py
│   ├── conversation_repository.py
│   ├── note_repository.py
│   ├── memory_repository.py
│   └── telemetry_repository.py
├── domain/
│   ├── settings_snapshot.py  # Settings data contract
│   ├── system_snapshot.py    # System health contract
│   ├── conversation.py       # Conversation data contract
│   ├── note.py              # Note data contract
│   ├── memory_item.py       # Memory data contract
│   └── tool_execution.py    # Tool execution contract
├── ui/
│   ├── app.py               # Main command palette window
│   ├── controller.py        # UI bridge (bus, state_store)
│   ├── tray.py              # System tray controller
│   ├── views/               # UI views (Chat, Notes, Settings, etc.)
│   ├── components/          # Reusable UI components
│   └── theme/               # Theme tokens
├── db/
│   ├── connection.py        # SQLite connection helpers
│   └── schema.sql           # Database schema
└── tools/
    └── tool_registry.py      # Tool registration
```

## Technology Stack

- **Language**: Python 3.11+ (Native ARM64 required)
- **UI Framework**: CustomTkinter (modern Tkinter wrapper)
- **Database**: SQLite with FTS5
- **AI Runtime**: Ollama (local LLM)
- **Architecture Pattern**: Event-driven, state-machine, service-oriented
- **Platform**: Windows ARM64

## Constitutional Governance

This architecture is governed by:
- **PROJECT_CONSTITUTION_V4.md** - Supreme authority
- **AGENTS.md** - Implementation directives for coding agents
- **ARCHITECTURE.md** - Repository policy and state ownership
- **ARCHITECTURE_ENFORCEMENT.md** - Implementation directives

Key constitutional invariants:
1. Ownership flow must be preserved
2. UI must be isolated from business logic
3. EventBus must be used for all runtime communication
4. Repositories must own persistence exclusively
5. ContextManager must gate all AI requests
6. No global state allowed
7. Regression budget is ZERO
