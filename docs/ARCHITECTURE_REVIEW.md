# Architecture Review — Settings Repository Alignment + Platform Readiness

**Date:** 2026-06-26  
**Scope:** Tracks 1.4 (settings alignment) and readiness assessment for Track 6.3 (plugin framework v2).  
**Author:** Cascade (AI pair programmer)

---

## 1. Track 1.4 Changes

### Problem

The settings layer had two competing repositories:

- `ai_command_center/core/settings/settings_repository.py` — an in-memory `dict` stub.
- `ai_command_center/repositories/settings_repository.py` — the canonical SQLite-backed repository used at runtime.

This duplication violated the AGENTS.md rule of **one canonical repository per concern** and risked tests or future services accidentally using the in-memory stub.

### Resolution

1. `core/settings/settings_repository.py` now re-exports the canonical `ai_command_center.repositories.settings_repository.SettingsRepository`. No new storage code was introduced.
2. `core/settings/settings_service.py` no longer accepts `repo=None`; the core service must receive an injected repository. This removes the in-memory fallback path.
3. `core/settings/settings_schema.py` was completed with all persisted fields (including `window_alpha`, `ollama_keep_alive`, `obsidian_vault_path`, `overlay_mode`) and full coercion/validation for `bool`, `int`, `float`, `str`, `Path`, and `Enum` choices.
4. `services/settings_service.py` now publishes the canonical `SettingsSnapshot` payload via `CoreSettingsService.get_snapshot().to_payload()` instead of building an ad-hoc dictionary from defaults.
5. `core/app_state.py` reducer now includes `window_alpha` and has a `_coerce_float` helper so the AppState projection matches the domain contract.

### Verification

- `python -m unittest discover tests` — **24/24 passed**.
- `verify_constitution.py`, `verify_contracts.py`, `verify_phase2.py`, `verify_phase4c.py`, `verify_phase5c.py`, `verify_capability_completion.py` — **PASS**.
- `Phase 5C daily driver stress test` — **PASS**.

---

## 2. Current Architecture Health

### Ownership Boundaries (AGENTS.md)

| Layer | Responsibility | Current State |
|---|---|---|
| **UI** | Render only; read `AppState`; write via `EventBus`/`UIController` | Compliant. Direct repository/service access has been removed. |
| **AppState** | Maintain snapshots; subscribe to `EventBus` | Compliant. All reducers are event-driven. |
| **EventBus** | Decouple layers | Compliant. Topics are canonical and versioned. |
| **Services** | Business logic; publish/subscribe via `EventBus` | Compliant. `BaseService` lifecycle is canonical; no direct service-to-service calls remain. |
| **Repositories** | Persistence; indexing | Compliant. `ApplicationCore` is the sole constructor of repositories. |
| **Storage** | SQLite/files | Owned by repositories only. |

### Settings Data Flow (after Track 1.4)

```text
SQLite
  → repositories.settings_repository.SettingsRepository
  → core.settings.settings_service.CoreSettingsService (schema, migration, SettingsSnapshot)
  → services.settings_service.SettingsService (EventBus I/O)
  → settings.snapshot
  → AppState reducer
  → UI render
```

The UI mutation path is unchanged:

```text
UI → settings.set_request → SettingsService → SQLite → settings.changed → settings.snapshot → AppState → UI
```

### Risks

| Risk | Status | Notes |
|---|---|---|
| `db/repository.py` still contains `SettingsRepository` | Legacy alias | It is wrapped by `repositories/settings_repository.py`. Safe to deprecate but not urgent. |
| `core/settings/settings_repository.py` is a re-export | Acceptable | Keeps the `core/settings` package API intact while unifying the implementation. |
| Settings value types from SQLite are strings | Managed | `SettingsSchema` coerces strings to `int`, `float`, `bool`, `Path` on read/write. |
| `vault_path` vs `obsidian_vault_path` | Minor | Both are present in `SettingsSnapshot` for historical compatibility; no conflict at runtime. |

---

## 3. Plugin Framework v2 (Implemented)

### What Track 6.3 Requires

- Dynamic enable/disable of plugins with restart.
- Extension isolation (extensions cannot disable core plugins).
- Persistent plugin state across restarts.

### Implementation

- Added `plugin_state` table to `ai_command_center/db/schema.sql`.
- Extended `PluginManifestRepository` with `load_enabled_states()` and `save_enabled_state()`.
- Added `service` field to `PluginManifest` so a plugin can declare its primary service.
- Updated `PluginRegistryService` to:
  - Merge persisted state over manifest defaults on load.
  - Persist state changes on enable/disable.
  - Publish `plugin.state_changed` with `pending_restart`.
  - Publish `service.restart_request` when the plugin declares a service.
- Added `SERVICE_RESTART_REQUEST` topic and made `ServiceManager` subscribe to it; it performs `stop()` then `start()` for the named service.
- Wired `PluginManifestRepository` into `PluginRegistryService` in `application.py`.
- Changed `shell.yaml` from `kind: core` to `kind: extension` with `service: shell_tool` to provide a real extension test target.

### Event Flow

```text
UI → plugin.disable_request { id: "shell" }
  → PluginRegistryService
    → validate (not core)
    → PluginManifestRepository.save_state(id, enabled=false)
    → plugin.state_changed { id: "shell", enabled: false, pending_restart: true }
    → service.restart_request { service: "shell_tool" }
  → ServiceManager (subscriber)
    → stop(shell_tool)
    → start(shell_tool)
  → AppState reducer
  → UI render
```

### Isolation Strategy

- **Core plugins** are protected by the registry service.
- **Extension plugins** declare bus topics and a primary service in their manifests.
- No direct repository access from services outside the plugin registry; no direct service calls.

### Conclusion

Plugin Framework v2 is **implemented without ownership-boundary violations**.

---

## 4. Recommended Next Steps

1. **Track 6.4 — Vector Search / Memory Graph**
   - Add an `EmbeddingService` that computes embeddings and publishes `memory.embedding_added`.
   - Use a vector repository for storage; keep all service communication via EventBus.

2. **Track 6.5 — Multi-Agent Runtime**
   - Introduce an `AgentService` that spawns agents as lightweight state machines.
   - Agents publish intents through the EventBus; no direct service calls.

---

## 5. Sign-off

All current architecture boundaries are intact. Track 1.4 and Track 6.3 are complete.
