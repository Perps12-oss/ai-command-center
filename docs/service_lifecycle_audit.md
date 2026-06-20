# Service Lifecycle Audit

## Summary

The shared lifecycle contract now lives in `ai_command_center/services/base.py` and exposes:

- `start()`
- `stop()`
- `get_state()`

Every service now publishes lifecycle events through the event bus.

## Current compliance

| Service | Status |
| --- | --- |
| `SettingsService` | Compliant |
| `ToolRegistryService` | Compliant |
| `ToolExecutorService` | Compliant |
| `TelemetryService` | Compliant |
| `ObsidianService` | Compliant |
| `SessionService` | Compliant via shared base |
| `MemoryGraphService` | Compliant via shared base |
