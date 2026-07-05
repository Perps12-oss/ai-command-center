# GOVERNANCE

PROJECT_CONSTITUTION_V4.md is the supreme authority.

Before any implementation:

1. Read Constitution.
2. Read Architecture.
3. Read Contracts.
4. Produce Constitutional Pre-Flight.

Implementation may not begin before pre-flight completion.

---

# AI Command Center � Implementation Directives for Coding Agents

## Objective

Refactor the application into a state-driven command center architecture.

The implementation must enforce the following ownership boundaries:

```text
UI
 ?
AppState
 ?
EventBus
 ?
Services
 ?
Repositories
 ?
Storage
```

Do not redesign the UI during this task. Keep UI behavior intact while moving business logic out of the UI layer.

---

## Non-Negotiable Rules

### Rule 1 � UI isolation

UI components may never:

- access files directly
- access SQLite directly
- access settings files directly
- call Ollama directly
- call tools directly

UI must only interact through:

- `EventBus`
- `AppState`
- `SettingsService`
- repositories (via services only)

### Rule 2 � No global state

Forbidden:

```python
GLOBAL_MODEL
CURRENT_VAULT
CURRENT_SETTINGS
```

State must flow through:

- `AppState`
- `SettingsSnapshot`

### Rule 3 � No direct service-to-service calls

Forbidden:

```python
service_a.call(service_b)
```

Required:

```python
service_a.publish(...)
service_b.subscribe(...)
```

via `EventBus`.

---

## Canonical Domain Models

Create and use the following domain modules under `ai_command_center/domain/`:

- `settings_snapshot.py`
- `system_snapshot.py`
- `conversation.py`
- `note.py`
- `memory_item.py`
- `tool_execution.py`
- `plugin_manifest.py`
- `service_state.py`
- `telemetry_event.py`

Rules:

- These are the only approved data contracts for runtime domain data.
- Use `dataclasses`.
- Do not use plain dictionaries for domain objects inside services or UI.

---

## Settings Layer

Create and use the following modules under `ai_command_center/core/settings/`:

- `settings_schema.py`
- `settings_service.py`
- `settings_repository.py`
- `migration_manager.py`

### SettingsSnapshot

Create a single source of truth for settings:

```python
SettingsSnapshot(
    model_name,
    provider,
    vault_path,
    theme,
    overlay_hotkey,
    telemetry_enabled,
)
```

### Validation

Support:

- `bool`
- `int`
- `float`
- `str`
- `Path`
- `Enum` choices

Reject invalid values and apply defaults automatically.

### Migration support

Support `schema_version` and automatic migration from one schema version to the next.

---

## Repository Layer

Create and use the following modules under `ai_command_center/repositories/`:

- `conversation_repository.py`
- `notes_repository.py`
- `memory_repository.py`
- `settings_repository.py`
- `telemetry_repository.py`

Responsibilities:

- persistence
- retrieval
- indexing

Repositories own storage. No other layer accesses storage directly.

---

## EventBus Topics

The existing `EventBus` remains the backbone. Add and document explicit topics.

Required topics:

- `settings.updated`
- `service.started`
- `service.ready`
- `service.stopped`
- `service.error`
- `conversation.updated`
- `notes.indexed`
- `tool.started`
- `tool.completed`
- `tool.failed`
- `telemetry.event`
- `system.snapshot`

Document every topic in the source or docs.

---

## Service Lifecycle Framework

Create a lifecycle base under `ai_command_center/services/base_service.py`.

Required states:

- `STOPPED`
- `STARTING`
- `READY`
- `DEGRADED`
- `ERROR`
- `STOPPING`

Every service must expose:

```python
get_state()
```

and publish state changes to `EventBus`.

---

## Tool Runtime

Create the following modules under `ai_command_center/tools/`:

- `tool_registry.py`
- `tool_executor.py`

### ToolRegistry

Responsibilities:

- `register_tool()`
- `list_tools()`
- `describe_tool()`

No execution logic.

### ToolExecutor

Responsibilities:

- `execute()`
- `cancel()`
- `get_status()`

Execution only.

### Tool result contract

Use `ToolExecution` from `ai_command_center/domain/tool_execution.py`.

---

## Telemetry Layer

Create and use the following modules under `ai_command_center/telemetry/`:

- `telemetry_service.py`

Capture:

- command execution
- tool execution
- service state changes
- note indexing
- chat requests
- errors

Publish `TelemetryEvent` to `EventBus`.

---

## AppState

Create a state module under `ai_command_center/core/state/app_state.py`.

Purpose:

- maintain current snapshots
- expose streams such as:
  - `recent_commands`
  - `recent_tool_runs`
  - `service_states`
  - `system_snapshot`
  - `telemetry_feed`

AppState subscribes to `EventBus` and UI reads from AppState.

---

## UI Contract

UI becomes a renderer only.

UI responsibilities:

- display state
- display telemetry
- display service health
- send commands

UI may not:

- perform business logic
- manage persistence
- manage services

---

## Deliverables

Refactor the codebase so that:

```text
UI -> AppState -> EventBus -> Services -> Repositories -> Storage
```

is strictly enforced.

Remove architecture violations and document every contract and topic.

Provide a dependency diagram showing final ownership boundaries in `docs/ARCHITECTURE.md` or the relevant architecture docs.

---

## Cursor Cloud specific instructions

Environment: Linux x86_64, Python 3.12. Dependencies are refreshed automatically by the
startup update script (`pip install --user` of `requirements.txt` + `requirements-test.txt`).
The `python3-tk` system package is also required (customtkinter imports `tkinter`) and is
already present in the VM snapshot — do not add it to the update script.

Non-obvious caveats:

- **The GUI (`main.py`) is Windows-ARM64 only.** `main()` calls `is_arm64()` and returns exit
  code 1 immediately on this x86_64 host, so the desktop app cannot be launched here. Develop
  and verify against the headless core (`ai_command_center.application.create_application`) and
  the `pytest` suite instead.
- **Headless bootstrap requires `APPDATA`.** `get_runtime_data_dir()` raises `OSError` when
  `APPDATA` is unset (it locates the SQLite DB dir, normally `%APPDATA%/AICommandCenter`). Run
  headless code with e.g. `APPDATA=/tmp/aicc_appdata`. No X display is needed — the core (incl.
  `customtkinter.CTkImage` hero asset) loads without one.
- **`create_application()` + `core.startup()`** wires 19 services (all report `READY`) and can
  drive a real chat round-trip via `StubOllamaService` (EventBus → AppState → chat.*) with no
  network. External services (Ollama on :11434, OpenAI, an Obsidian vault) are all optional and
  mocked in tests; nothing external needs to run.
- **Console scripts** (`pytest`, `ruff`, `bandit`, `coverage`) install to `~/.local/bin`, which
  is not on `PATH`. Invoke them as `python3 -m pytest` / `python3 -m ruff` etc.

Common commands (see `README_TESTING.md` and `.github/workflows/` for the source of truth):

- Tests: `python3 -m pytest` (coverage auto-enabled via `pytest.ini`; ~2 min; 5 Windows/ARM64
  tests auto-skip). Fast subset: `python3 -m pytest -m "not slow"`.
- Lint: `python3 -m ruff check ai_command_center` and
  `python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json`.
- Governance gates: `python3 scripts/verify_constitution.py`, then
  `python3 tools/ucgs_runner.py > .ucgs_last.yaml` and `python3 tools/ucgs_ci_gate.py .ucgs_last.yaml`.
