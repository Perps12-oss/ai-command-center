# Architecture Integrity Audit Report

## Scope

This audit scans the repository for violations of the architecture contract defined in `AGENTS.md` and `docs/ARCHITECTURE_ENFORCEMENT.md`.

The review focuses on runtime modules under `ai_command_center/`, plus the UI and service layers that participate in app behavior.

## Summary

| Violation type | Findings |
| --- | ---: |
| Direct file access outside repositories | 10 |
| SQLite access outside repositories | 1 |
| UI component calling services directly | 0 |
| Service calling another service directly | 5 |
| EventBus topic string literal not defined in `topics.py` | 6 |
| Settings access bypassing `SettingsService` | 1 |
| Domain object represented as raw dict | 1 |

## Findings

| File | Line | Violation type | Recommended remediation |
| --- | ---: | --- | --- |
| `ai_command_center/db/connection.py` | 20 | Direct SQLite access outside repositories | Move DB connection/bootstrap into the repository package (or a dedicated persistence service) and keep the connection module private. |
| `ai_command_center/db/connection.py` | 29 | Direct file access outside repositories | Read schema assets through a repository/bootstrap helper rather than reading files directly from the connection module. |
| `ai_command_center/services/obsidian_service.py` | 78 | Settings access bypassing `SettingsService` | Subscribe to `settings.snapshot`/`settings.updated` or request settings through a service facade instead of reading the repository directly. |
| `ai_command_center/services/obsidian_service.py` | 227 | Direct file access outside repositories | Move vault file writes into a repository or storage adapter; keep the service orchestration-only. |
| `ai_command_center/services/obsidian_service.py` | 232 | Direct file access outside repositories | Move note file writes into a repository layer. |
| `ai_command_center/services/obsidian_service.py` | 252 | Direct file access outside repositories | Replace direct markdown reads with a note repository method. |
| `ai_command_center/services/obsidian_service.py` | 338 | Direct file access outside repositories | Replace direct file reads with repository-backed note access. |
| `ai_command_center/services/plugin_registry_service.py` | 65 | Direct file access outside repositories | Load plugin manifests via a plugin repository/manifest loader rather than reading YAML directly in the service. |
| `ai_command_center/platform/detector.py` | 185 | Direct file access outside repositories | Route runtime metadata persistence through a repository or config service. |
| `ai_command_center/platform/detector.py` | 194 | Direct file access outside repositories | Route runtime metadata reads through a repository layer. |
| `ai_command_center/ui/layer/background_spec.py` | 45 | UI direct file access | Move spec loading behind a repository/service boundary so the UI remains a renderer. |
| `ai_command_center/ui/layout/compiler.py` | 59 | UI direct file access | Load layout assets through a repository/service boundary instead of the UI layer. |
| `ai_command_center/ui/spatial/spec.py` | 14 | UI direct file access | Move spatial-spec loading behind a repository/service boundary. |
| `ai_command_center/services/chat_handler_service.py` | 104 | Service calling another service directly | Replace direct calls to `ObsidianService` with an event-driven contract (e.g. `note.selected`, `context.snapshot_created`). |
| `ai_command_center/services/chat_handler_service.py` | 108 | Service calling another service directly | Replace direct calls to `MemoryGraphService` with an event-driven contract. |
| `ai_command_center/services/chat_handler_service.py` | 114 | Service calling another service directly | Replace direct calls to `SessionService` with an event-driven contract. |
| `ai_command_center/services/chat_handler_service.py` | 189 | Service calling another service directly | Replace direct session mutation with an event-driven command or repository-backed workflow. |
| `ai_command_center/services/chat_handler_service.py` | 192 | Service calling another service directly | Replace direct LLM invocation with an event-driven workflow (e.g. request/response bus events). |
| `ai_command_center/ui/controller.py` | 48 | EventBus topic string literal not defined in `topics.py` | Import and use `UI_PALETTE_OPEN`/related constants from `ai_command_center/core/events/topics.py`. |
| `ai_command_center/ui/controller.py` | 67 | EventBus topic string literal not defined in `topics.py` | Replace string topic with a constant exported by `topics.py`. |
| `ai_command_center/services/settings_service.py` | 41 | EventBus topic string literal not defined in `topics.py` | Replace `"settings.set_request"` with a constant from `topics.py`. |
| `ai_command_center/ui/app.py` | 204 | EventBus topic string literal not defined in `topics.py` | Replace hard-coded UI topics with the central topic registry. |
| `ai_command_center/services/plugin_registry_service.py` | 48 | EventBus topic string literal not defined in `topics.py` | Move plugin event names into the topic registry. |
| `ai_command_center/services/obsidian_service.py` | 75 | EventBus topic string literal not defined in `topics.py` | Replace `"note.select"` with a canonical topic constant. |
| `ai_command_center/db/conversation_repository.py` | 48 | Domain object represented as raw dict | Replace `list[dict[str, object]]` with the canonical `Conversation` model. |

## Notes

- No current UI component was found calling a service directly; the architecture boundary is mostly intact in that regard.
- The largest remaining architecture debt is in persistence ownership and event-topic normalization.
- The next remediation pass should focus on moving file I/O behind repositories and replacing all raw EventBus topic literals with constants from `ai_command_center/core/events/topics.py`.
