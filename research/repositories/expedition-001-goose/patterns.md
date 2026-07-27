---
repository: block/goose
expedition_id: expedition-001-goose
---

# Goose — Extracted Pattern Candidates and Validation Notes

This file holds the raw pattern candidates extracted from the Goose expedition. Validated patterns are promoted to `research/patterns/PAT-NNN.md` and the Pattern Registry.

## C-001 — Provider abstraction with `Provider` trait + `MessageStream`

- **Where:** `crates/goose-provider-types/src/base.rs` (`Provider` trait, `MessageStream`, `ProviderMetadata`), `crates/goose/src/providers/provider_registry.rs`.
- **Problem:** Multiple LLM providers (OpenAI, Anthropic, Ollama, etc.) need a uniform streaming interface while preserving per-provider metadata and token usage.
- **Solution:** A single `Provider` trait with `stream` and `complete` methods returning `MessageStream` of `(Option<Message>, Option<ProviderUsage>)`. A `ProviderRegistry` registers `ProviderDef` implementations with metadata and constructor closures.
- **Validation:**
  - [x] Strengthens ACC without replacing authority model — yes, applies to Capability Runtime.
  - [x] Simpler than ACC's current provider model? Not obviously; ACC already has `OllamaServiceBase` + `OllamaHttpService` + stub. However, Goose's trait-based registry is more general.
  - [x] Integrates through canonical EventBus path? Yes, `ChatHandlerService` can dispatch to a provider registry.
  - [x] Unwanted dependencies? No new runtime assumptions beyond HTTP client.
- **Decision:** **Validate** → promote to `PAT-001`.

## C-002 — MCP extension runtime with tool cache and env denylist

- **Where:** `crates/goose/src/agents/extension_manager.rs`, `crates/goose/src/agents/extension.rs` (`ExtensionConfig`, `Envs`).
- **Problem:** External tools must be discovered, loaded, sandboxed, and called without name collisions or environment injection.
- **Solution:** Extensions are MCP servers spawned as stdio/HTTP/unix-socket processes. `ExtensionManager` caches tools, invalidates the cache on changes, and `Envs` validates a denylist of dangerous environment variables.
- **Validation:**
  - [x] Strengthens ACC — yes, `ToolExecutorService` could host an MCP adapter.
  - [x] Simpler? Adds process complexity, but the denylist and caching are clean.
  - [x] Integrates through canonical path — tool invocations already flow through `ToolExecutorService` / `EventBus`.
  - [x] Dependencies? Requires `rmcp` or an MCP Python SDK; process lifecycle risk.
- **Decision:** **Validate** → promote to `PAT-002`.

## C-003 — Per-session creation lock + LRU agent cache

- **Where:** `crates/goose/src/execution/manager.rs` (`AgentManager`).
- **Problem:** Concurrent requests for the same session must not initialize MCP servers twice, and long-lived processes must not leak memory from unbounded cached agents.
- **Solution:** `AgentManager` uses an `LruCache<String, Arc<Agent>>` plus a `HashMap<String, Arc<Mutex<()>>>` of per-session creation locks. Locks are pruned when `Arc::strong_count` reaches 1.
- **Validation:**
  - [x] Strengthens ACC — yes, `ServiceManager` / headless core can adopt.
  - [x] Simpler? Yes, isolated concurrency pattern.
  - [x] Integrates through canonical path — applies to service lifecycle, not authority.
  - [x] Dependencies? None beyond `lru` / `asyncio.Lock`.
- **Decision:** **Validate** → promote to `PAT-003`.

## C-004 — Cancellation token registry per active session

- **Where:** `crates/goose/src/execution/manager.rs` (`try_register_cancel_token`, `cancel_session`).
- **Problem:** Users need to cancel an in-progress chat or tool call, and the runtime must distinguish busy vs idle sessions.
- **Solution:** A `HashMap<String, CancellationToken>` per `AgentManager`. A token is registered at reply start, cancelled on user request, and removed on completion.
- **Validation:**
  - [x] Strengthens ACC — yes, `OllamaHttpService.cancel` and `ToolExecutorService` can use this.
  - [x] Simpler? Yes, additive.
  - [x] Integrates through canonical path — `EventBus` `tool.cancelled`, `chat.cancelled`.
  - [x] Dependencies? `asyncio.Event` / `CancellationToken` equivalents exist.
- **Decision:** **Validate** → promote to `PAT-004`.

## C-005 — Layered config with ENV / YAML / keyring precedence and migrations

- **Where:** `crates/goose/src/config/base.rs`, `crates/goose/src/config/migrations.rs`, `crates/goose/src/config/paths.rs`.
- **Problem:** Configuration must support system defaults, user files, environment overrides, secrets, and schema evolution.
- **Solution:** `Config` reads `/etc/goose/config.yaml`, `GOOSE_ADDITIONAL_CONFIG_FILES`, `~/.config/goose/config.yaml`; ENV overrides; keyring/file secrets; `migrations.rs` rewrites legacy keys.
- **Validation:**
  - [x] Strengthens ACC — yes, `SettingsService` already exists but could borrow precedence/migration ideas.
  - [x] Simpler? Adds migration machinery; ACC already has `migration_manager.py` placeholder.
  - [x] Integrates through canonical path — `SettingsService` and `SettingsSnapshot`.
  - [x] Dependencies? None major; Python `keyring` or file fallback.
- **Decision:** **Validate with adaptation** → promote to `PAT-005`.

## C-006 — Conversation compaction with visibility metadata

- **Where:** `crates/goose/src/context_mgmt/mod.rs`, `crates/goose-provider-types/src/conversation.rs`.
- **Problem:** Long conversations exceed model context limits; summarization must preserve user-facing history.
- **Solution:** `compact_messages` summarizes agent-visible messages, marks originals `user_visible` only, and injects an agent-visible summary plus continuation instruction.
- **Validation:**
  - [ ] Strengthens without replacing authority? Yes, but touches `State Authority` / conversation repository.
  - [ ] Simpler? Complex; requires token counting and summarization model.
  - [ ] Integrates through canonical path? Yes, via `conversation.updated` and `AppState`.
  - [ ] Dependencies? Needs a summarization capability.
- **Decision:** **Needs more analysis** — hold as candidate, do not promote yet.

## C-007 — Tool inspection + permission pipeline

- **Where:** `crates/goose/src/tool_inspection.rs`, `crates/goose/src/security/`, `crates/goose/src/config/permission.rs`.
- **Problem:** Tool calls need pre-execution security/egress/repetition checks and user approval policies.
- **Solution:** `ToolInspectionManager` runs inspectors, produces `InspectionResult` with `action` (`Allow`, `RequireApproval`, `Block`). `PermissionManager` stores per-tool levels.
- **Validation:**
  - [x] Strengthens ACC — yes, `ToolExecutorService` permission checks can be enriched.
  - [x] Simpler? More modular than hard-coded shell allow/deny.
  - [x] Integrates through canonical path — `ToolExecutorService` and `PermissionService`.
  - [x] Dependencies? Inspector implementations are additive.
- **Decision:** **Validate** → promote to `PAT-006`.

## C-008 — Layered telemetry (tracing + optional OTel/Langfuse/PostHog)

- **Where:** `crates/goose/src/logging.rs`, `crates/goose/src/tracing/`, `crates/goose/src/otel/`, `crates/goose/src/posthog.rs`.
- **Problem:** Observe a distributed async agent without locking into one backend.
- **Solution:** `tracing-subscriber` with file + console + `EnvFilter` layers; optional `opentelemetry-otlp`, `langfuse_layer`, and PostHog events.
- **Validation:**
  - [x] Strengthens ACC — `TelemetryService` already captures events; this adds structured tracing backends.
  - [x] Simpler? Incremental; can be layered behind feature flags.
  - [x] Integrates through canonical path — `TelemetryEvent` on `EventBus`.
  - [x] Dependencies? Python tracing libraries (OpenTelemetry, Langfuse) are available.
- **Decision:** **Validate** → promote to `PAT-007`.

## C-009 — Cron-based scheduled recipe engine

- **Where:** `crates/goose/src/scheduler.rs`, `crates/goose/src/scheduler_trait.rs`.
- **Problem:** Run agent workflows on a schedule.
- **Solution:** `tokio-cron-scheduler` + JSON persistence + `CancellationToken` per running job.
- **Validation:**
  - [ ] Strengthens ACC? Potentially duplicates `Goal Scheduler`.
  - [ ] Simpler? No; adds cron runtime and persistence.
  - [ ] Integrates through canonical path? Could, but conflicts with ACC Goal Scheduler responsibility.
  - [ ] Dependencies? Cron parser, job scheduler.
- **Decision:** **Hold** — conflict with ACC Goal Scheduler; revisit if needed.

## C-010 — Gateway abstraction for external chat platforms

- **Where:** `crates/goose/src/gateway/`.
- **Problem:** Allow Telegram/SMS/etc. to interact with Goose sessions.
- **Solution:** `Gateway` trait, `GatewayManager`, pairing store, `GatewayHandler` routing messages into sessions.
- **Validation:**
  - [ ] Strengthens ACC? Out of current scope.
  - [ ] Simpler? No; adds external platform lifecycle.
  - [ ] Integrates through canonical path? Could, but not a current ACC priority.
  - [ ] Dependencies? Platform SDKs, pairing/auth model.
- **Decision:** **Hold** — future consideration only.
