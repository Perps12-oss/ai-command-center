---
repository: block/goose
expedition_id: exp-001
url: https://github.com/block/goose
status: Validated
language: Rust
owner: Agent 2
date_started: 2026-07-26
date_completed: 2026-07-27
---

# Repository Expedition Report: block/goose

## Executive Summary

block/goose is a Rust-native, open-source AI agent that ships as a desktop app, CLI, and embeddable API. It is part of the Agentic AI Foundation (AAIF) at the Linux Foundation. The codebase is a multi-crate Rust workspace with strong separation between core runtime, provider adapters, MCP tooling, and platform bindings.

| Field | Value |
|-------|-------|
| Verdict | Proceed |
| Key strengths | Async runtime, provider registry, MCP extension manager, context compaction, tool inspection pipeline |
| Key risks | Subprocess-based extensions require trust model; Rust-only cannot be ported directly into Python ACC |
| Recommended next step | Adapt selected patterns through Integration Proposals and Architecture Review |

## Repository Structure

```text
goose/
├── crates/
│   ├── goose/              # Core agent runtime
│   ├── goose-cli/          # CLI entry point
│   ├── goose-mcp/          # MCP server tooling
│   ├── goose-providers/    # Provider trait and utilities
│   ├── goose-provider-types/
│   ├── goose-sdk/          # SDK for embedding
│   ├── goose-local-inference/
│   ├── goose-download-manager/
│   └── goose-test, goose-test-support
├── bin/                    # Distributions
├── documentation/
└── Cargo.toml              # Workspace manifest
```

Dependency direction: `goose-cli` -> `goose` -> `goose-providers` / `goose-provider-types`. `goose-mcp` provides server-side MCP helpers.

## Runtime

- tokio `rt-multi-thread` executor
- `Agent::reply` is the main async turn loop
- `SessionExecutionMode`: `Interactive`, `Background`, `SubTask { parent_session }`
- `CancellationToken` passed through tool dispatch
- `tool_stream` merges `ServerNotification` stream, `action_required` stream, and the final result future

## Provider Layer

- `Provider` trait defined in `goose_providers`
- `ProviderDef` trait plus `ProviderRegistry` / `ProviderEntry` in `goose`
- Inventory resolvers: `inventory_identity` and `inventory_configured` for UI model picker
- Declarative custom providers via JSON config in `custom_providers/`
- `normalize_model_config` backfills `context_limit` from provider metadata
- TLS config passed from central config

## Extension System

- `ExtensionConfig` enum: `stdio`, `streamable_http`, `builtin`, `platform`, `frontend`, `inline_python` (SSE deprecated)
- `ExtensionManager` owns a `HashMap<String, Extension>` and a cached tool list
- `Envs` validates disallowed environment variables (PATH, LD_PRELOAD, etc.)
- `env_keys` pull secrets from `Config` / keyring and substitute into `envs`, headers, and URIs
- Multi-transport: Tokio child process, streamable HTTP, Unix domain socket, inline Python via uvx

## Tool Execution

- Agent categorizes tools as Shell / Read / Write / Other
- `ToolInspectionManager` runs a pipeline of inspectors: Security, Egress, Adversary, Permission, Repetition
- `ToolConfirmationRouter` registers tool requests and awaits user confirmation
- `ToolCallContext` carries `session_id`, `working_dir`, `tool_call_request_id`
- `ToolCallResult` bundles an async result, an optional notification stream, and an optional action-required stream

## State Management

- `Session` struct captures id, working_dir, name, type, usage, conversation, extension_data, recipe, model_config, goose_mode, parent_session_id
- `SessionManager` is a thin wrapper over `SessionStorage`
- `SessionStorage` uses sqlx + SQLite with WAL mode, schema version 15, `BEGIN IMMEDIATE` migrations
- Lazy connection pool via `tokio::sync::OnceCell`
- `SessionUpdateBuilder` for partial, typed updates

## Context Assembly

- `prepare_tools_and_prompt` collects enabled extension tools, system prompt, and model config
- `context_mgmt::compact_messages` summarizes older messages when token ratio exceeds `GOOSE_AUTO_COMPACT_THRESHOLD`
- `MessageMetadata` controls `user_visible` vs `agent_visible`
- `format_message_for_compacting` serializes tool pairs for summarization
- `apply_structured_summary` parses a structured summary and renders it to markdown

## Desktop Architecture

- `GoosePlatform` enum (`GooseDesktop` / `GooseCli`)
- `goose_apps` module and `acp` module implement an Agent-Client Protocol server (axum)
- `acp/server` has endpoints for sessions, providers, extensions, dictation, recipes, slash commands, etc.
- Frontend tools are dispatched through message passing back to the desktop UI

## Configuration

- Global `Config` with typed `get_param`/`get_secret` and keyring-backed storage
- `GooseMode` controls permission defaults (approve, chat, etc.)
- `DeclarativeProviderConfig` JSON for custom providers
- Permission levels stored per tool name

## Logging & Observability

- `tracing` + `tracing-subscriber` with env filter
- Optional OpenTelemetry features (`otel`)
- `posthog.rs` telemetry behind `telemetry` feature
- Security findings emitted as structured tracing events with `security.event_type`

## Testing

- `goose-test` and `goose-test-support` crates
- `mockall`, `wiremock`, `test-case`, `serial_test`, `insta`
- Unit tests embedded in source files
- `env-lock` for deterministic environment in tests

## Performance

- `Cargo.toml` strips debug info for dependency packages only (`profile.dev.package."*"`)
- `tokio-cron-scheduler` for scheduled recipes
- `lru` cache dependency
- Conversation compaction + tool-pair summarization to manage context windows
- `token_counter` and `usage_estimator` for cost tracking

## Pattern Candidates

| ID | Pattern | Subsystem | Initial Assessment |
|----|---------|-----------|-------------------|
| PC-001 | Declarative Provider Registry with Inventory State | providers/init.rs, provider_registry.rs | Strong fit for ACC provider/catalog needs |
| PC-002 | MCP Extension Manager with Multi-Transport | agents/extension_manager.rs | Relevant, but subprocess trust model needs adaptation |
| PC-003 | Conversation Context Compaction with Visibility Metadata | context_mgmt/mod.rs | Strong fit for ACC conversation / memory management |
| PC-004 | Tool Inspector / Confirmation Router Pipeline | agents/tool_execution.rs, permission, security | Strong fit for ACC tool governance |
| PC-005 | SQLite Session Storage with Schema Migrations | session/session_manager.rs | Moderate; overlaps ACC repository pattern |
| PC-006 | Modular Tool Inspection and Permission Pipeline | tool_inspection.rs, security/, permission/ | Strong fit for ACC tool governance |
| PC-007 | Layered Telemetry with Pluggable Backends | logging.rs, tracing/, otel/, posthog.rs | Strong fit for ACC telemetry service |

## Integration Opportunities

| Pattern | Priority | Effort | Risk | Recommendation |
|---------|----------|--------|------|----------------|
| PC-001 Provider Registry | High | Medium | Low | Adapt into ACC settings/provider catalog |
| PC-003 Context Compaction | High | Medium | Low | Adapt for conversation/memory management |
| PC-004 Tool Inspector Pipeline | High | Medium | Low | Adapt for tool execution authority |
| PC-006 Modular Tool Inspection / Permission | High | Medium | Low | Adapt into ACC tool governance |
| PC-007 Layered Telemetry Backends | Medium | Low | Low | Adapt into ACC telemetry exporter interface |
| PC-002 MCP Extension Manager | Medium | High | Medium | Future; evaluate runtime provider interface |
| PC-005 SQLite Session Storage | Low | Medium | Low | Future; only if needed beyond repository layer |

## Risk Analysis

- **Authority risk:** Goose runs tools in subprocesses and has permission levels, but it is not a Workspace OS. ACC must keep its State/Execution authority model.
- **Security risk:** Subprocess extensions can execute arbitrary code. ACC's existing runtime approval model should not be weakened.
- **Porting risk:** Rust patterns cannot be copied verbatim into Python. Extract the design, not the code.
- **Dependency risk:** Some capabilities (Ollama, MCP, OAuth, local inference) are optional features. ACC can choose which to adopt.

## Final Recommendation

**Proceed** with formal pattern validation for PC-001, PC-003, PC-004, PC-006, and PC-007. Hold PC-002 and PC-005 for later. Do not port Goose's UI or runtime; extract engineering patterns only.

## Notes

- A more detailed subsystem-by-subsystem analysis from an earlier pass is archived in [`notes/legacy_goose_expedition_report.md`](./notes/legacy_goose_expedition_report.md).
