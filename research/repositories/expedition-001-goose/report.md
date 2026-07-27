---
repository: block/goose
expedition_id: expedition-001-goose
url: https://github.com/block/goose
status: Validated
owner: Agent 1
date_started: 2026-07-26
date_completed: 2026-07-26
---

# Repository Expedition Report: Goose (`block/goose`)

## Executive Summary

Goose is a native, open-source AI agent written in Rust. It ships as a desktop application (Electron + Vite), a full terminal CLI (`goose-cli`), and an embeddable library/crate set (`goose`, `goose-providers`, `goose-mcp`, `goose-sdk`, etc.). The project supports 15+ LLM providers and 70+ extensions via the Model Context Protocol (MCP), and is part of the Linux Foundation Agentic AI Foundation.

This expedition was selected as the pilot for the ACC Engineering Intelligence Framework. The goal was to extract engineering patterns that could strengthen AI Command Center without replacing its canonical authority chain (Execution Authority → Goal Scheduler → Planner → Execution Orchestrator → Capability Runtime → Evidence Collection → Receipts → State Authority → Workspace State → UI).

**High-level verdict: Proceed.** Goose contains several mature, isolated patterns—especially around provider abstraction, MCP extension runtime, async cancellation, configuration/secrets management, and conversation compaction—that can be adapted into ACC. Its overall architecture is conversation-centric and uses more global mutable state than ACC permits, so we recommend **borrowing implementation patterns, not architectural philosophy**.

## Architecture

### Repository structure

The workspace is split into focused crates:

- `crates/goose` — core runtime: `agents`, `config`, `context_mgmt`, `execution`, `gateway`, `providers`, `recipe`, `scheduler`, `security`, `session`, `skills`, `sources`, `tracing`, `otel`.
- `crates/goose-cli` — terminal interface (`cli.rs`, `main.rs`, `commands/`).
- `crates/goose-providers` — concrete provider implementations (OpenAI, Anthropic, Ollama, Databricks, Google, etc.).
- `crates/goose-provider-types` — shared provider trait, `ModelConfig`, `Conversation`, `Message`, `MessageStream`, `ProviderMetadata`.
- `crates/goose-mcp` — bundled MCP servers (memory, autovisualiser, computercontroller, tutorial, peekaboo).
- `crates/goose-sdk` / `crates/goose-sdk-types` — C/Rust bindings and custom ACP request types.
- `crates/goose-local-inference` — optional local Whisper/LLM inference with Candle.
- `crates/goose-test-support` / `crates/goose-test` — shared test fixtures.
- `ui/desktop` — Electron/Vite/React/TypeScript desktop app; `ui/goose-binary` / `ui/text` provide alternative frontends.

### Layering and dependency direction

```text
UI / CLI / API / Gateway
         |
execution::AgentManager  (LRU session cache, cancellation registry)
         |
    agents::Agent        (reply loop, tool dispatch, retry, compaction)
         |
+--------+--------+-------+
|                 |
agents::ExtensionManager   providers::ProviderRegistry + Provider
|                 |
MCP clients (stdio/HTTP/sock)   HTTP provider clients
|                 |
Local tools / extensions        Remote LLM APIs
```

State flows through `session::SessionManager` (SQLite), `config::Config` (YAML + keyring), and in-memory `Agent`/`ExtensionManager` instances. Notably, Goose uses several global/static singletons (`Config::global()`, `SESSION_STORAGE`, `AGENT_MANAGER`, `ActionRequiredManager::global()`) which conflicts with ACC's Rule 2 (no global state).

### Key modules and responsibilities

| Module | Responsibility |
|--------|----------------|
| `execution/manager.rs` | `AgentManager` — LRU cache of `Arc<Agent>`, per-session creation locks, `CancellationToken` registry, session removal. |
| `agents/agent.rs` | Main agent orchestration: `reply`/`reply_internal`, tool categorization, dispatch, retry, hooks, conversation compaction trigger. |
| `agents/extension_manager.rs` | MCP client lifecycle, tool caching/invalidation, resource/prompt access, OAuth fallback, tool dispatch. |
| `agents/extension.rs` | `ExtensionConfig` enum, `Envs` denylist, `ExtensionInfo`, `ToolInfo`. |
| `agents/tool_execution.rs` | `ToolCallContext`, `ToolCallResult`, `handle_approval_tool_requests`, `handle_frontend_tool_request`. |
| `agents/mcp_client.rs` | `McpClient` trait, `GooseMcpHostInfo`, `GooseClient` wrapper over `rmcp` client. |
| `providers/base.rs` + `goose-provider-types/src/base.rs` | `Provider` trait, `MessageStream`, `ProviderMetadata`, `ConfigKey`, `ModelInfo`. |
| `providers/provider_registry.rs` | `ProviderRegistry` with `ProviderDef`, `ProviderEntry`, metadata, inventory resolvers. |
| `session/session_manager.rs` | SQLite persistence, migrations, usage ledger, session CRUD, conversation storage. |
| `context_mgmt/mod.rs` | Conversation compaction: `compact_messages`, `check_if_compaction_needed`. |
| `scheduler.rs` | Cron-based scheduled recipes using `tokio-cron-scheduler`. |
| `config/base.rs` | Global `Config` with YAML/ENV/keyring precedence, migrations, typed getters via `pastey` macros. |
| `logging.rs` / `tracing/` / `otel/` / `posthog.rs` | Layered tracing, optional OpenTelemetry, Langfuse observer, PostHog telemetry. |

## Runtime

- **Async runtime:** `tokio` multi-thread (`rt-multi-thread`). `goose-cli/src/main.rs` uses `#[tokio::main]`.
- **Agent lifecycle:** `AgentManager::get_or_create_agent` checks an `LruCache`; misses take a per-session `Arc<Mutex<()>>` creation lock to prevent duplicate `initialize` calls to MCP servers. On eviction, creation locks are pruned by `Arc::strong_count`.
- **Cancellation:** `AgentManager` registers a `CancellationToken` per busy session. `cancel_session` triggers it; `remove_session` cancels and evicts.
- **Tool execution flow:** `Agent::reply` builds `ReplyContext`, calls `provider.stream(...)`, handles tool requests, routes approved calls through `dispatch_tool_call` to `ExtensionManager::dispatch_tool_call`, which calls `McpClient::call_tool`. Results are wrapped in `ToolCallResult` with optional notification/action streams.
- **Subagents:** `agents/subagent_handler.rs` runs `run_subagent_task` for delegated tasks.
- **Gateways:** `gateway/manager.rs` and `gateway/handler.rs` route external chat platform messages (Telegram, etc.) into sessions with pairing codes and `CancellationToken`-backed tasks.

## State Management

- **Session record:** `Session` (`session/session_manager.rs`) is a large serializable struct with `id`, `working_dir`, `name`, `session_type`, `extension_data`, `usage`, `accumulated_usage`, `conversation`, `provider_name`, `model_config`, `goose_mode`, etc. It is persisted to SQLite (`sessions.db`, schema version 15).
- **Conversation:** `Conversation` (`goose-provider-types/src/conversation.rs`) is a validated `Vec<Message>` with `agent_visible_messages()` / `user_visible_messages()` filters and message merging/coalescing logic.
- **Message visibility:** `MessageMetadata` controls `agent_visible` and `user_visible` flags. Compaction preserves user-visible history while replacing agent-visible history with a summary.
- **Token accounting:** `Usage` / `ProviderUsage` track input/output/total/cache tokens. `SessionUsageTotals` reconcile a ledger table in SQLite.
- **Extension state:** `EnabledExtensionsState` and per-session `ExtensionData` are serialized into the session row.
- **App state:** There is no central immutable AppState store like ACC's `AppStateStore`. State is split across the SQLite `SessionManager`, global `Config`, and in-memory `Agent`/`ExtensionManager` caches.

## Providers

- **Provider trait** (`goose-provider-types/src/base.rs`):
  ```rust
  #[async_trait]
  pub trait Provider: Send + Sync {
      fn get_name(&self) -> &str;
      async fn stream(&self, model_config: &ModelConfig, system: &str, messages: &[Message], tools: &[Tool]) -> Result<MessageStream, ProviderError>;
      async fn complete(...) -> Result<(Message, ProviderUsage), ProviderError>;
      async fn get_context_limit(&self, model_config: &ModelConfig) -> Result<usize, ProviderError>;
      fn retry_config(&self) -> RetryConfig;
      async fn fetch_supported_models(&self) -> Result<Vec<String>, ProviderError>;
      async fn fetch_recommended_models(&self, toolshim: bool) -> Result<Vec<String>, ProviderError>;
  }
  ```
- **MessageStream:** `Pin<Box<dyn Stream<Item = Result<(Option<Message>, Option<ProviderUsage>), ProviderError>> + Send>>`. Providers emit partial messages and tool-call chunks; `collect_stream` coalesces them.
- **ModelConfig** (`goose-provider-types/src/model.rs`) carries `model_name`, `context_limit`, `temperature`, `max_tokens`, `toolshim`, `toolshim_model`, `request_params`, `reasoning`, and `request_headers`. A canonical model registry (`canonical.rs`) backfills limits and reasoning support.
- **Provider registry** (`goose/src/providers/provider_registry.rs`): `ProviderEntry` stores metadata + constructor + inventory resolvers; `ProviderRegistry` registers `ProviderDef` implementations and supports custom/declarative providers.
- **Implementations:** `goose-providers/src/openai.rs`, `anthropic.rs`, `ollama.rs`, `databricks.rs`, `google.rs`, `snowflake.rs`, `http_status.rs`, `api_client.rs`; `goose/src/providers/*_def.rs` wraps them with Goose-specific metadata.

## Plugins / Extensions

- **MCP-first:** Goose extensions are Model Context Protocol servers. Types (`agents/extension.rs`):
  - `Stdio` (spawn process).
  - `Builtin` (bundled in `goose-mcp`).
  - `InlinePython`.
  - `Sse` (deprecated).
  - Streamable HTTP / Unix socket clients (`ExtensionManager`).
- **ExtensionManager** (`agents/extension_manager.rs`):
  - Spawns stdio processes via `tokio::process::Command`.
  - Wraps `rmcp` client (`McpClient`).
  - Caches tools with an atomic `tools_cache_version` and invalidates on add/remove.
  - Reads resources and prompts from MCP servers.
  - Performs OAuth fallback on auth failures.
- **Security:** `Envs` denylist blocks `PATH`, `LD_PRELOAD`, `DYLD_INSERT_LIBRARIES`, `NODE_OPTIONS`, `PYTHONPATH`, `ComSpec`, `TEMP`, etc. `ExtensionConfig` carries `timeout`, `env_keys`, `cwd`.
- **Tool name mangling:** `__` separator used to avoid collisions; `ExtensionManager` recovers dotted and prefixed names.

## UI

- **Desktop:** `ui/desktop` is an Electron + Vite + React/TypeScript app. It uses `forge.config.ts` for packaging and Playwright/Vitest for tests. The Rust backend is loaded as a binary/IPC layer.
- **CLI:** `goose-cli` uses `rustyline` (history/bindings), `cliclack` for prompts, `bat` for syntax highlighting, and `console` for styling.
- **goose_apps:** `goose_apps/app.rs`, `cache.rs`, `resource.rs` support embedded HTML apps and resource caching.
- **Gateway:** `gateway/manager.rs` + `handler.rs` plus `telegram.rs` let Goose respond to messages from external platforms (Telegram, etc.) with pairing codes and session routing.

## Tool Execution

- **Lifecycle:** `ToolRequest` → `Agent::categorize_tools` → frontend vs extension routes. Frontend tools execute in the UI; extension tools go through `ExtensionManager`.
- **Approval flow:** `tool_confirmation_router.rs` registers pending confirmations. `handle_approval_tool_requests` yields an `ActionRequired` message, awaits `confirmation_rx`, then either dispatches or records a declined response. `Permission::AlwaysAllow`/`AlwaysDeny` update `PermissionManager`.
- **Inspection:** `tool_inspection.rs` (`ToolInspectionManager`) runs `SecurityInspector`, `EgressInspector`, `AdversaryInspector`, `RepetitionInspector` before dispatch.
- **Dispatch:** `Agent::dispatch_tool_call` calls `ExtensionManager::dispatch_tool_call`, which resolves the owning extension, calls `McpClient::call_tool`, and returns `ToolCallResult`.
- **Results:** `ToolCallResult` contains a future for the final `CallToolResult` plus optional `ServerNotification`/`Message` streams.
- **Receipts:** ACC has a more formal Receipt system; Goose records tool responses inside the `Conversation` and `Session` usage ledger.

## Security

- **Permission model:** `config::permission::PermissionManager` maps tool names to `PermissionLevel` (`AlwaysAllow`, `AllowOnce`, `Ask`, `NeverAllow`).
- **Inspectors:** `security/` and `tool_inspection.rs` provide prompt-injection, egress, adversarial, and repetition checks.
- **Secrets:** `Config` uses the system keyring when `system-keyring` feature is enabled, otherwise a `secrets.yaml` file with `0o600` permissions. Environment variables take precedence.
- **Env sandbox:** `Envs` denylist prevents extensions from overriding security-relevant environment variables.
- **File safety:** `scheduler.rs` opens schedule recipes with `O_NOFOLLOW` (Unix) and `0o600` permissions; `copy_bounded_schedule_recipe` limits size to 1 MiB.

## Testing

- **Unit tests:** Embedded `#[cfg(test)]` modules inside source files (e.g., `agents/agent.rs` has many tests).
- **Integration tests:** `crates/goose/tests/acp_common_tests/mod.rs` contains a large shared ACP test suite driven against in-memory transport.
- **Support crates:** `goose-test-support` / `goose-test` provide fixtures and mocks.
- **Mocking:** `mockall` for trait mocks, `wiremock` for HTTP, `tempfile` for directories.
- **CI:** GitHub workflows under `.github/workflows/`. Linting via workspace-level clippy/deny config.

## Performance

- **Session cache:** `LruCache` of `Arc<Agent>` bounded by `GOOSE_MAX_ACTIVE_AGENTS` (default 100).
- **Tool cache:** `ExtensionManager` caches `Arc<Vec<Tool>>` and bumps a `tools_cache_version` on add/remove; `get_all_tools_cached` returns the cached copy.
- **Compaction:** `context_mgmt::compact_messages` summarizes the conversation when token usage exceeds a threshold (default 0.8 of context limit). Original messages become user-visible only; summary becomes agent-visible only.
- **Parallelism:** `rayon` for CPU-bound work, `tokio` for I/O. `goose-cli` review orchestrator runs checks in parallel.
- **Lazy loading:** Providers and extensions are constructed on first use per session; model inventory is fetched on demand.

## Pattern Candidates

| ID | Pattern | Subsystem | Initial Assessment |
|----|---------|-----------|--------------------|
| C-001 | Provider abstraction with `Provider` trait + `MessageStream` | Providers | Strong candidate for ACC capability runtime |
| C-002 | MCP extension runtime with tool cache and denylist | Extensions | Strong candidate for capability runtime |
| C-003 | Per-session creation lock + LRU agent cache | Runtime | Strong candidate for agent/session management |
| C-004 | Cancellation token registry per active session | Runtime | Strong candidate for cancellation |
| C-005 | Layered config (ENV / YAML / keyring) with migrations | Configuration | Adaptable; ACC already has settings schema |
| C-006 | Conversation compaction with visibility metadata | State / Context | Adaptable for long context handling |
| C-007 | Tool inspection + permission pipeline | Security | Adaptable for ACC capability execution |
| C-008 | Layered telemetry (tracing + optional OTel/Langfuse/PostHog) | Observability | Adaptable |
| C-009 | Cron-based scheduled recipe engine | Scheduler | Future consideration |
| C-010 | Gateway abstraction for external chat platforms | UI / Desktop | Future consideration |

## Interesting Patterns

- **Provider `MessageStream`:** A single `Stream` of `(Option<Message>, Option<ProviderUsage>)` unifies partial text, tool-call chunks, and usage. `collect_stream` folds it into a final message. This is a clean pattern ACC could adopt for `OllamaService`/`ChatHandlerService` streams.
- **Provider registry with `ProviderDef`:** Implementing types expose `metadata()` and `from_env()`; the registry stores a constructor closure and inventory resolvers. This is an inversion-of-control pattern that maps well to ACC's service factory.
- **ExtensionManager tool cache:** An atomic `tools_cache_version` and `Mutex<Option<Arc<Vec<Tool>>>>` allows cheap `get_all_tools_cached` while guaranteeing invalidation on dynamic extension changes.
- **AgentManager creation locks:** A per-session `Arc<Mutex<()>>` stored in a `HashMap` prevents multiple concurrent callers from each initializing the same MCP servers; the lock is pruned when `Arc::strong_count` reaches 1.
- **Config precedence and migrations:** `Config` loads `/etc/goose/config.yaml`, `GOOSE_ADDITIONAL_CONFIG_FILES`, then `~/.config/goose/config.yaml`, with ENV overrides and keyring/file secrets. `migrations.rs` rewrites legacy keys before use.
- **Message visibility metadata:** `MessageMetadata` distinguishes `agent_visible` vs `user_visible`. Compaction uses these flags to preserve user-facing history while summarizing model-facing context.

## Things to Avoid

- **Global/static singletons:** `Config::global()`, `SESSION_STORAGE` LazyLock, `AGENT_MANAGER` OnceCell, `ActionRequiredManager::global()`. These violate ACC Rule 2 (no global state) and Rule 3 (state flows through `AppState` / `SettingsSnapshot`).
- **Agent as a god object:** `Agent` holds `provider`, `extension_manager`, `prompt_manager`, `tool_inspection_manager`, `retry_manager`, `hook_manager`, etc. ACC already separates these into services; do not collapse them.
- **Direct `tokio::runtime::Handle::try_current` in `Drop`:** `ActionRequiredStream::drop` spawns an async task from a destructor. This is fragile and can panic outside a runtime.
- **Conversation-centric state authority:** Goose's `SessionManager` owns workspace state indirectly through `working_dir`. ACC's `Workspace Graph` and `State Authority` are the canonical owners; do not replace them.
- **Rust-specific assumptions:** `Pin<Box<dyn Stream>>`, `Arc<Mutex<...>>`, and `tokio::select!` cannot be copied directly into Python; use Pythonic equivalents (`asyncio`, `EventBus`, `AppState`).

## Integration Opportunities

| Pattern | Priority | Effort | Risk | Recommendation |
|---------|----------|--------|------|----------------|
| C-001 Provider abstraction | High | Medium | Low | **Adapt** — introduce a capability-provider protocol and registry in ACC |
| C-002 MCP extension runtime | High | Medium | Low | **Adapt** — wrap MCP clients as capability runtimes via adapter |
| C-003 Per-session creation locks + LRU cache | Medium | Small | Low | **Adopt** in `ServiceManager`/`Agent` lifecycle |
| C-004 Cancellation token registry | Medium | Small | Low | **Adopt** for long-running chat/tool operations |
| C-005 Layered config + migrations | Medium | Medium | Medium | **Adapt** into `SettingsService` migration manager |
| C-006 Conversation compaction | Low | Large | Medium | **Future** — only if long-context issues arise |
| C-007 Tool inspection pipeline | Medium | Medium | Medium | **Adapt** to augment `ToolExecutorService` |
| C-008 Layered telemetry | Low | Medium | Low | **Adapt** to enrich `TelemetryService` |
| C-009 Cron scheduler for recipes | Low | Large | High | **Future** — conflicts with ACC Goal Scheduler |
| C-010 Gateway abstraction | Low | Large | High | **Future** — out of scope for current UI |

## Risk Analysis

- **Architectural risks:** Adopting Goose's conversation-centric `Agent`/`Session` model would weaken ACC's `Execution Authority`, `Goal Scheduler`, `Planner`, and `State Authority`. All patterns must be adapted to plug into the existing ACC pipeline.
- **Global state risk:** Any pattern that relies on `Config::global()` or static `LazyLock` must be converted to ACC's `SettingsSnapshot` + `AppState` model.
- **Dependency risk:** MCP introduces child-process lifecycle management, stdio/HTTP transport failures, and extension malware concerns. ACC would need a robust runtime adapter.
- **Language/runtime risk:** Rust idioms (`Pin`, `dyn Stream`, `tokio`) do not map 1:1 to Python. Adaptation is required, not copy-paste.
- **Constitutional risk:** Replacing ACC's `Receipt System`, `Workspace Graph`, `Truth Boundary`, or `World Model` with Goose equivalents is forbidden.

## Final Recommendation

- **Decision: Proceed** with targeted pattern extraction.
- **Immediate:** Promote C-001, C-002, C-003, C-004 to the Pattern Registry and draft Integration Proposals.
- **Near-term:** Validate C-005, C-007, C-008 as candidates and create Integration Proposals if Architecture Review agrees.
- **Future/hold:** C-006, C-009, C-010 require deeper analysis and are not recommended now.
- **Next step:** Submit the validated patterns and Integration Proposals to Architecture Review (Tom) before any runtime implementation.
