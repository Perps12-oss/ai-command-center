# Architecture Audit

## Dependency boundary summary

### UI
- UI code may read `AppState` and publish intents to `EventBus`.
- UI does not directly depend on repositories or storage.

### Services
- Services depend on repositories through the repository package.
- Services publish state changes through `EventBus`.
- Services do not call each other directly.

### Repositories
- Repositories own persistence and may contain SQLite or file-system access.
- The runtime now routes through the repository package so storage access is centralized.

## Flagged areas

- `ai_command_center/db/connection.py` still owns database bootstrapping and schema creation.
- The old `db` modules remain the underlying storage implementation; repository wrappers are the new architectural boundary.
- Future work should replace direct repository imports in service modules with the repository package everywhere.
