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

## 3. Plugin Framework v2 Feasibility Assessment

### What Track 6.3 Requires

- Dynamic enable/disable of plugins with restart.
- Extension isolation (extensions cannot disable core plugins).
- Persistent plugin state across restarts.

### Current State

- `PluginRegistryService` reads YAML manifests from `plugins/manifests/` and publishes `plugin.catalog`.
- It handles `plugin.enable_request` and `plugin.disable_request` in memory only; core plugins are protected.
- There is no persistence for enabled/disabled state.
- There is no dynamic loading/unloading of extension code.

### Can It Be Implemented Without Ownership Violations?

**Yes, with three additions:**

#### 1. Add a `PluginManifestRepository` for persistence

The repository already exists (`ai_command_center/repositories/plugin_manifest_repository.py`). It should be extended to store the enabled/disabled state in SQLite, keyed by plugin ID. The repository layer owns storage; the service layer owns the business rule that core plugins cannot be disabled.

#### 2. Add a `PluginLifecycleService` (or extend `PluginRegistryService`) that only publishes events

When a plugin is enabled/disabled, the service should:

- Validate the request (core plugins protected).
- Persist the new state via the repository.
- Publish `plugin.state_changed`.
- If the plugin requires a service restart, publish `service.restart_request`.

It must **not** call `service.start()` or `service.stop()` directly.

#### 3. Extend `ServiceManager` to listen to `service.restart_request`

Currently `ServiceManager` is invoked imperatively by `ApplicationCore.startup()` and `shutdown()`. To maintain the architecture, `ServiceManager` should subscribe to `service.restart_request` on the EventBus and perform the actual stop/start sequence. This keeps service lifecycle ownership inside `ServiceManager` while still honoring the no-direct-service-calls rule.

### Proposed Event Flow

```text
UI → plugin.disable_request { id: "notes" }
  → PluginRegistryService
    → validate (not core)
    → PluginManifestRepository.save_state(id, enabled=false)
    → plugin.state_changed
    → service.restart_request { service: "obsidian" } (if plugin declares dependent services)
  → ServiceManager (subscriber)
    → stop(obsidian)
    → start(obsidian)
    → service.ready / service.error
  → AppState reducer
  → UI render
```

### Isolation Strategy

- **Core plugins** are protected by the registry service itself.
- **Extension plugins** can declare bus topics and tool specs in their manifests; they are loaded by a `PluginLoader` that registers them with `ToolRegistry` and `EventBus`. The loader only publishes registration events; it never touches repositories or other services directly.
- **Sandboxing**: Python does not provide true sandboxing. Extension isolation should be limited to:
  - No direct repository access (enforced by architecture rules and code review).
  - No direct service calls (enforced by architecture).
  - Extension tools/topics are registered into shared registries; misbehaving extensions can be disabled by the registry service.

### Conclusion

Plugin Framework v2 is **feasible without introducing ownership-boundary violations**, provided that:

1. Plugin state is persisted through the existing repository layer.
2. Plugin changes are communicated via the EventBus only.
3. `ServiceManager` is taught to restart services via EventBus subscription, rather than being invoked imperatively from another service.
4. Dynamic extension loading is handled by a dedicated loader that only publishes registration events.

---

## 4. Recommended Next Steps

1. **Track 6.3 — Plugin Framework v2**
   - Persist plugin enabled/disabled state in `PluginManifestRepository`.
   - Add `service.restart_request` topic and make `ServiceManager` subscribe to it.
   - Add a `PluginLoader` that registers extension tools/topics through the EventBus.

2. **Track 6.4 — Vector Search / Memory Graph**
   - Add an `EmbeddingService` that computes embeddings and publishes `memory.embedding_added`.
   - Use a vector repository for storage; keep all service communication via EventBus.

3. **Track 6.5 — Multi-Agent Runtime**
   - Introduce an `AgentService` that spawns agents as lightweight state machines.
   - Agents publish intents through the EventBus; no direct service calls.

---

## 5. Sign-off

All current architecture boundaries are intact. Track 1.4 is complete. Track 6.3 is ready for implementation without violating the ownership rules in `AGENTS.md`.
