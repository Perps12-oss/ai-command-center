# Expedition Notes: block/goose

This folder contains supporting notes for the Goose pilot expedition. The canonical deliverables are `../report.md`, `../patterns.md`, `../decisions.md`, plus the cross-referenced pattern cards and integration proposals.

## Key source locations reviewed

- `crates/goose/src/agents/agent.rs` — `Agent`, `AgentConfig`, `reply`, `reply_internal`, `dispatch_tool_call`.
- `crates/goose/src/execution/manager.rs` — `AgentManager`, LRU cache, creation locks, cancellation registry.
- `crates/goose/src/session/session_manager.rs` — `Session`, `SessionManager`, SQLite schema/migrations, usage ledger.
- `crates/goose/src/agents/extension_manager.rs` — `ExtensionManager`, MCP clients, tool cache, OAuth fallback.
- `crates/goose/src/agents/extension.rs` — `ExtensionConfig`, `Envs` denylist, `ExtensionInfo`/`ToolInfo`.
- `crates/goose/src/agents/tool_execution.rs` — tool approval, frontend tool requests, `ToolCallResult`.
- `crates/goose/src/context_mgmt/mod.rs` — conversation compaction and visibility metadata.
- `crates/goose/src/providers/provider_registry.rs` — `ProviderRegistry`, `ProviderDef`, metadata/constructors.
- `crates/goose/src/config/base.rs` — `Config`, layered precedence, migrations, secrets.
- `crates/goose/src/scheduler.rs` — `Scheduler`, cron jobs, JSON persistence.
- `crates/goose/src/logging.rs`, `tracing/`, `otel/`, `posthog.rs` — telemetry layers.
- `crates/goose/src/gateway/` — `GatewayManager`, `GatewayHandler`, chat platform integration.
- `ui/desktop` — Electron/Vite/React/TypeScript frontend.
- `crates/goose/src/goose_apps/` — embedded HTML apps and resource caching.

## Search tooling used

Temporary Python scripts in `%TEMP%` were used to locate symbols across the local Goose clone because the workspace `grep_search` tool could not access `C:\Users\S8633\AppData\Local\Temp\goose` directly. These scripts were not committed.

## Open questions / held patterns

- `C-006` conversation compaction needs a deeper token-counting and summarization capability review.
- `C-009` cron scheduler may overlap with ACC `Goal Scheduler`; defer.
- `C-010` gateway abstraction is out of current scope.
