# Repository Migration Report

## Goal

Move persistence access behind repository interfaces so services do not reach into storage directly.

## Current status

- `SettingsService` now uses the repository boundary in `ai_command_center/repositories/settings_repository.py`.
- `ObsidianService` uses the repository wrapper for notes.
- `SessionService` and `MemoryGraphService` can be pointed at the repository wrappers without changing their public behavior.
- The underlying storage implementation remains SQLite-backed for now, but the repository package is now the canonical dependency boundary.

## Migration target

| Domain | Repository wrapper | Storage implementation |
| --- | --- | --- |
| Settings | `ai_command_center.repositories.settings_repository.SettingsRepository` | SQLite-backed `db.repository.SettingsRepository` |
| Notes | `ai_command_center.repositories.notes_repository.NotesRepository` | SQLite-backed `db.note_repository.NoteRepository` |
| Conversation | `ai_command_center.repositories.conversation_repository.ConversationRepository` | SQLite-backed `db.conversation_repository.ConversationRepository` |
| Memory | `ai_command_center.repositories.memory_repository.MemoryRepository` | SQLite-backed `db.memory_repository.MemoryRepository` |
| Telemetry | `ai_command_center.repositories.telemetry_repository.TelemetryRepository` | SQLite-backed `db.telemetry_repository.TelemetryRepository` |
