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

### Plugin registry (5B+ v2)

```text
plugins/manifests/*.yaml → PluginManifestRepository
                                              ↓
PluginRegistryService → plugin.catalog → PluginsView
       ↓
plugin.enable_request / plugin.disable_request
       ↓
SQLite plugin_state (persist)
plugin.state_changed
service.restart_request { service: "..." }
       ↓
ServiceManager → stop(service) → start(service)
```

- Core plugins cannot be disabled.
- Extension plugin state persists in SQLite.
- Toggling an extension with a declared `service` triggers a `service.restart_request`.
- `ServiceManager` listens to restart requests and performs the actual lifecycle sequence.

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

## Event topic registry

Canonical topic constants live in `ai_command_center/core/events/topics.py`.

| Topic | Producer | Consumers | Payload |
|-------|----------|-----------|---------|
| `settings.updated` | SettingsService | AppState, UI | `{"key": str, "value": Any}` |
| `settings.snapshot` | SettingsService | AppState, ObsidianService, UI | full settings projection |
| `service.started` | BaseService | AppState, telemetry | `{"service": str}` |
| `service.ready` | BaseService | AppState, telemetry | `{"service": str}` |
| `service.stopped` | BaseService | AppState, telemetry | `{"service": str}` |
| `service.error` | BaseService | AppState, telemetry | `{"service": str, "detail": str}` |
| `service.state_changed` | BaseService | AppState | `{"name": str, "state": str, "detail": str}` |
| `tool.started` | ToolExecutorService | UI, telemetry | `{"tool": str, "invoke_id": str}` |
| `tool.completed` | ToolExecutorService | UI, telemetry | `{"tool": str, "invoke_id": str}` |
| `tool.failed` | ToolExecutorService | UI, telemetry | tool failure payload |
| `telemetry.event` | TelemetryService | future UI/analytics | normalized telemetry event |
| `system.snapshot` | SystemSnapshotBuilder | AppState | canonical system snapshot |

---

## Roadmap status

Full ownership stack (Tracks 1–3, 4–5, 6.3): **complete**.

| Track | Goal | Status |
|-------|------|--------|
| 1 | Foundation — domain models, settings layer, repositories | ✅ |
| 2 | Runtime engine — EventBus topics, service lifecycle, tool runtime | ✅ |
| 3 | State & observability — AppState projection, telemetry, snapshots | ✅ |
| 4 | UI contract compliance — isolation, chat, memory/notes/plugins/Workspace OS | ✅ |
| 5 | Feature completion — Workspace OS, markdown, memory/notes/plugins/settings polish | ✅ |
| 6.1–6.3 | Component gallery, design tokens, plugin framework v2 | ✅ |
| 6.4 | Vector search / memory graph enhancements | ⏳ next |
| 6.5 | Multi-agent runtime | ⏳ gated — see `docs/ARCHITECTURE_REVIEW_MULTI_AGENT.md` |

**Residual risks:**
- `core/settings/settings_repository.py` re-export vs `repositories/settings_repository.py` may confuse contributors.
- `app.py` still subscribes to many EventBus topics directly; replace with AppState subscriptions as projection grows.
- `tools/tool_executor.py` is a stub — execution happens inside `ToolExecutorService`.

---

## Gate history

Current phase: **Phase 6 — IN PROGRESS**
Previous snapshot: Phase 5 complete at commit `3970aa5` / tag `phase-5-complete-20260620`

| Gate | Script | Result |
|------|--------|--------|
| Phase 1–3D | `verify_phase*.py` | PASS |
| Contracts | `verify_contracts.py` | PASS |
| Phase 4A | `verify_phase4a.py` | PASS |
| Phase 4B | `verify_phase4b.py` | PASS |
| Phase 4C | `verify_phase4c.py` | PASS |
| Phase 4D | `verify_phase4d_compression.py` | PASS |
| Phase 4E | `verify_phase4e.py` | PASS |
| Phase 4F | `verify_phase4f.py` | PASS |
| Phase 5A | `verify_phase5a.py` | PASS |
| Phase 5B | `verify_phase5b.py` | PASS |
| Phase 5C preflight | `verify_phase5c_preflight.py` | PASS |
| Phase 5C gate | `verify_phase5c.py` | PASS |
| Phase 5C+ telemetry | `verify_phase5c_telemetry.py` | PASS |
| Capability completion | `verify_capability_completion.py` | PASS |
| Note audits | `audit_note_integration.py` | PASS |
| Daily driver | `run_daily_driver.py` | PASS |
| Constitution | `verify_constitution.py` | PASS |

UCGS v3: **STRICT** | Phase: 6 | Verdict: `IN_PROGRESS`
