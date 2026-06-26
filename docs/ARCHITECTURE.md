# AI Command Center — Architecture

See [ARCHITECTURE_ENFORCEMENT.md](ARCHITECTURE_ENFORCEMENT.md) for the implementation directives that coding agents must follow when modifying this repository.

## Data flow (target)

```text
UI → EventBus → Services → EventBus → AppState → UI
```

No shortcuts. UI never calls services or repositories directly.

Bootstrap (`ApplicationCore.startup()` → `services.load_all()`) is a **documented exception** — wiring purity adds no value at cold start.

---

## Repository access policy

**Only `ApplicationCore` (via `create_application()`) may construct or hold repository instances.**

| Layer | May access repositories? |
|-------|--------------------------|
| `ApplicationCore` / `create_application()` | Yes — composition root only |
| Services | Yes — injected at registration time by ApplicationCore |
| UI | **Never** |
| Scripts / tests | Prefer EventBus; diagnostics may use debug-mode bus taps |

Repositories are not exposed on `ApplicationCore` public fields.

---

## UI communication policy

UI modules may use **only**:

1. **EventBus** — publish intents (`settings.set_request`, `ui.command`, …)
2. **AppState** — read `AppStateStore.snapshot` and subscribe to state changes

UI receives `bus` and `state_store` — **not** `ApplicationCore`, `ServiceManager`, or repositories.

`UIController(bus, state_store)` is the sole UI bridge.

UI must **not**:

- Import `db.repository`
- Import `application.ApplicationCore` for runtime wiring
- Call `ServiceManager.get()` for mutations
- Call service methods directly

---

## Official hotkey

| Setting | Value |
|---------|--------|
| **Default** | `Alt+Space` |
| **Stored in** | `settings.hotkey` → `settings.snapshot` |
| **Not used** | `Win+Space` — conflicts with Windows language switching |

Tray icon remains fallback if global hook registration fails.

---

## Command routing

```text
UI → ui.command → CommandRouterService → command.routed → Phase 3 handlers
```

### `command.routed` payload

```json
{
  "text": "user input",
  "intent": "chat | shell | note_search | note_new | navigate",
  "args": {},
  "status": "pending"
}
```

Phase 3 services subscribe to `command.routed` by intent (Ollama chat, Obsidian, etc.).

AppState projection: `last_command`, `last_command_intent` updated via reducer.

---

## Context manager (required before Ollama)

**Every AI request** must call `ContextManager.build_context()` before `OllamaService`.

Phase 3 V1:

```python
bundle = context_manager.build_context(
    query,
    clipboard=None,  # explicit per request — not background monitoring
    notes=None,
)
# OllamaService receives bundle.prompt only
```

See [PHASE3.md](PHASE3.md) for scope bans and [PHASE4.md](PHASE4.md) for Phase 4 modules.

Phase 4D adds `conversation_summary` compression and `graph_snippets` opt-in.

---

## Phase 4 event flows

### Tool execution (4B)

```text
command.routed (shell) → ShellToolService → tool.invoke → ToolExecutorService → tool.result
```

### Model routing (4F)

```text
command.routed (chat) → ChatHandler → ModelRouterService.resolve() → model.selected → OllamaHttpService
```

### Memory graph (4E)

```text
memory.remember → MemoryGraphService → memory.stored
memory.select → MemoryGraphService → memory.selected → ContextManager (opt-in)
```

### Telemetry (5C+)

```text
EventBus → TelemetryService (raw passthrough) → telemetry_events (SQLite)
scripts/telemetry_summary.py → offline correlation + SESSION SUMMARY
```

**Firewall:** PASSIVE WITH DERIVED OFFLINE INTELLIGENCE

- Runtime: dumb camera only — no inference, no bus publish, no behavioral classification.
- Offline: hesitation, retry, command correlation, friction score in `telemetry_summary.py` only.
- Telemetry optional — removing `TelemetryService` does not break core flows.

### Plugin registry (5B)

```text
plugins/manifests/*.yaml → PluginRegistryService → plugin.catalog → PluginsView
plugin.enable_request / plugin.disable_request (extension only; core protected)
```

### Overlay (4C)

```text
ui.palette_open → overlay.show → UI (compact | palette geometry)
settings.set_request → settings.snapshot → AppState → SettingsView
```

---

## State ownership

Two kinds of state — both intentional, no refactor required.

### Operational state (authoritative — lives in services)

Runtime lifecycle inside the service process.

Examples:

- `ServiceState.READY`
- `ServiceState.STARTING`
- `ServiceState.DEGRADED`
- `ServiceState.ERROR`

**Source of truth:** `BaseService._state`  
**UI visibility:** mirrored into `AppState.services` via `service.state_changed` events.

### Presentation state (UI-consumable projection — lives in AppState)

Derived snapshots for rendering.

Examples:

- `service_status` (from `ServiceSnapshot`)
- `settings` (from `settings.snapshot`)
- `last_error`
- `phase`

**Source of truth:** `AppStateStore` reducers only — never write AppState from services directly.

---

## Settings

SQLite → `repositories.settings_repository.SettingsRepository` (canonical) → `core.settings.settings_service.CoreSettingsService` (schema/migration) → `services.settings_service.SettingsService` (EventBus I/O) → **`settings.snapshot`** event → AppState reducer.

The compatibility re-export in `core/settings/settings_repository.py` ensures the canonical repository is the only one used; the old in-memory stub has been removed.

### `settings.snapshot` payload

```json
{
  "theme": "dark",
  "accent": "#3B82F6",
  "default_model": "llama3.2:3b",
  "ollama_url": "http://localhost:11434",
  "hotkey": "alt+space",
  "low_memory_mode": false,
  "window_width": 1100,
  "window_height": 700,
  "window_alpha": 0.95,
  "obsidian_vault_path": "",
  "overlay_mode": "palette",
  "telemetry_enabled": true,
  "schema_version": 1
}
```

Payload is produced from `SettingsSnapshot.to_payload()`. Emitted on service load and after every settings write.

### UI mutation path

```text
UI publishes settings.set_request { "key": "...", "value": "..." }
    → SettingsService handles
    → SQLite updated
    → settings.changed (incremental)
    → settings.snapshot (full projection)
    → AppState updated
    → UI re-renders from snapshot
```

---

## EventBus wildcard policy

**Wildcard subscriptions are forbidden in production code.**

Forbidden outside debug/diagnostics:

- `bus.subscribe_all(handler)`
- `bus.subscribe("*", handler)`

Allowed:

- `AppStateStore` — topic-scoped subscriptions only
- `scripts/verify_*.py` — `EventBus(debug_mode=True)` for test taps
- Future diagnostics panel — explicit `debug_mode=True` bus instance

Rationale: wildcard listeners cause performance and debugging nightmares as plugins, logging, and analytics accumulate.

---

## Phase 2 approval checklist

| # | Requirement | Status |
|---|-------------|--------|
| 1 | Repository access policy documented | This document |
| 2 | `settings.snapshot` event + AppState reducer | Implemented |
| 3 | Service vs AppState ownership documented | This document |
| 4 | Wildcard EventBus restricted | `debug_mode` gate |

---

## Risk register (architecture)

| Risk | Status |
|------|--------|
| Event Bus | Healthy |
| AppState | Healthy |
| Service Manager | Healthy |
| Repository leakage | Mitigated — policy + private composition |
| Settings state | Fixed — `settings.snapshot` |
| Dual state ownership | Documented — operational vs presentation |
| Bootstrap lifecycle | Accepted exception |
| Wildcard events | Restricted |
| UI isolation | `UIController(bus, state_store)` — no ApplicationCore in UI |
| Command routing | `CommandRouterService` skeleton → `command.routed` |
| Hotkey | Official: **Alt+Space** |
| AI integration | Not started |
| Scope creep | None detected |
