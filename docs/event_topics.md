# Event Topic Registry

The runtime uses the canonical topic registry in `ai_command_center/core/events/topics.py`.

| Topic | Producer | Consumers | Payload contract |
| --- | --- | --- | --- |
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
