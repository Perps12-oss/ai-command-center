# Final Enforcement Gap Report

Date: 2026-06-20
Source of truth: code scan only (markdown documents not used for findings)

## Severity A

| File | Line | Category | Remediation Effort | Finding |
| --- | ---: | --- | --- | --- |
| ai_command_center/services/tool_executor_service.py | 51 | Service -> Service calls | M | ToolExecutorService takes ToolRegistryService directly and invokes it, creating direct service coupling. |
| ai_command_center/services/tool_executor_service.py | 58 | Service -> Service calls | M | Direct call to registry.get in service runtime path. |
| ai_command_center/services/tool_executor_service.py | 59 | Service -> Service calls | M | Direct call to registry.register in service runtime path. |
| ai_command_center/services/tool_executor_service.py | 93 | Service -> Service calls | M | Direct call to registry.get during tool invocation dispatch. |
| ai_command_center/ui/components/hero_panel.py | 38 | UI -> Storage access | S | UI component opens image file directly via PIL Image.open. |
| ai_command_center/ui/layer/background_image.py | 29 | UI -> Storage access | S | UI layer loads background file directly via Image.open. |
| ai_command_center/services/obsidian_service.py | 24 | Settings bypasses | M | Service imports SettingsRepository directly instead of using settings service/event contracts only. |
| ai_command_center/services/obsidian_service.py | 85 | Settings bypasses | M | Service reads obsidian_vault_path from settings repository directly. |
| ai_command_center/services/obsidian_service.py | 90 | Settings bypasses | M | Service reads obsidian_vault_path from settings repository helper path directly. |

## Severity B

| File | Line | Category | Remediation Effort | Finding |
| --- | ---: | --- | --- | --- |
| ai_command_center/services/obsidian_service.py | 283 | Direct file access outside repositories | M | Service reads note body directly with read_text instead of repository-only access. |
| ai_command_center/services/obsidian_service.py | 369 | Direct file access outside repositories | M | Service reads markdown file directly during indexing. |
| ai_command_center/services/plugin_registry_service.py | 66 | Direct file access outside repositories | M | Service reads manifest YAML file directly; should be moved behind repository boundary. |
| ai_command_center/platform/detector.py | 185 | Direct file access outside repositories | M | Platform code writes baseline file directly. |
| ai_command_center/platform/detector.py | 194 | Direct file access outside repositories | M | Platform code reads baseline file directly. |
| ai_command_center/services/obsidian_service.py | 83 | Topic literals | S | EventBus subscription uses string literal note.context.request instead of topic constant. |
| ai_command_center/services/obsidian_service.py | 114 | Topic literals | S | EventBus publish uses string literal note.context.result instead of topic constant. |
| ai_command_center/services/plugin_registry_service.py | 110 | Topic literals | S | EventBus publish uses string literal plugin.state_changed instead of topic constant. |

## Severity C

| File | Line | Category | Remediation Effort | Finding |
| --- | ---: | --- | --- | --- |
| ai_command_center/db/telemetry_repository.py | 32 | Dict contracts | M | fetch_since returns list[dict[str, Any]] rather than canonical TelemetryEvent contract. |
| ai_command_center/db/telemetry_repository.py | 55 | Dict contracts | M | fetch_session returns list[dict[str, Any]] rather than canonical TelemetryEvent contract. |
| ai_command_center/services/telemetry_summary.py | 195 | Dict contracts | M | Offline summary pipeline consumes dict-shaped telemetry rows instead of canonical telemetry model objects. |
| ai_command_center/db/connection.py | 17 | Infrastructure bootstrap exceptions | M | Global sqlite connect/bootstrap helper remains outside repository abstraction. |
| ai_command_center/db/connection.py | 26 | Infrastructure bootstrap exceptions | M | init_database performs schema bootstrap and migration orchestration centrally. |
| ai_command_center/db/connection.py | 29 | Infrastructure bootstrap exceptions | S | Schema script file is loaded directly from disk in bootstrap path. |
| ai_command_center/db/connection.py | 40 | Infrastructure bootstrap exceptions | M | Migration function for note FTS remains in central bootstrap module. |
| ai_command_center/db/connection.py | 78 | Infrastructure bootstrap exceptions | M | Migration function for memory graph remains in central bootstrap module. |
| ai_command_center/db/connection.py | 109 | Infrastructure bootstrap exceptions | M | Migration function for telemetry remains in central bootstrap module. |

## Totals

- Severity A findings: 9
- Severity B findings: 8
- Severity C findings: 9
- Total findings: 26

## Effort Legend

- S: small localized change, low sequencing risk
- M: medium refactor, touches contracts or multiple call sites
- L: large change, broad sequencing/migration impact
