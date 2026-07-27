# Goose → ACC Engineering Expedition Report

**Scope:** Read-only architectural study of `block/goose` (Rust) to identify mature engineering patterns that can strengthen AI Command Center (ACC) without displacing its authority-chain architecture.  
**Source repository:** `https://github.com/block/goose`, shallow clone of `main` (v1.44.0 workspace).  
**Study date:** Generated during implementation of the Goose → ACC expedition plan.  
**Constraint:** All analysis is read-only; no ACC code was modified. Any recommended borrowing must plug into the canonical ACC authority chain:

```text
User → Execution Authority → Goal Scheduler → Planner → Execution Orchestrator → Capability Runtime → Evidence Collection → Receipts → State Authority → Workspace State → UI
```

---

## Methodology

For each subsystem the study answers:

1. What problem does Goose solve?
2. How is it implemented?
3. Strengths / weaknesses
4. Does ACC already solve this?
5. Is Goose objectively better?
6. Can the implementation pattern be borrowed?
7. Architectural risks for ACC
8. Recommendation: Adopt / Adapt / Ignore / Future consideration

---

## 1. Repository Structure

**Purpose.** Package boundaries, dependency direction, and layering discipline.

**Implementation notes.** Goose is a Cargo workspace with clear crate ownership:

- `crates/goose` — core domain (agent loop, sessions, context, security, providers orchestration)
- `crates/goose-providers` — provider adapters (OpenAI, Anthropic, Ollama, Bedrock, Gemini, Azure, Databricks, many more)
- `crates/goose-provider-types` — shared wire/types/contracts consumed by providers and core
- `crates/goose-sdk` / `crates/goose-sdk-types` — external bindings for the Agent Client Protocol (ACP)
- `crates/goose-cli` — CLI entry point, depends only on `goose`, `goose-providers`, `goose-mcp`
- `crates/goose-mcp` — bundled MCP server with stdio/HTTP transports
- `crates/goose-local-inference` — on-device inference with `candle`
- `crates/goose-download-manager` — artifact downloads
- `crates/goose-test` / `crates/goose-test-support` — shared test utilities
- `ui/desktop` — Electron + React + Vite desktop application

`Cargo.toml` uses workspace-level dependency management, feature flags for TLS backends, optional providers, local inference, and telemetry. A `deny.toml` enforces dependency licensing. `crates/` boundaries make the dependency graph visible: `goose-cli` does not depend on `ui/desktop`, and `goose-providers` does not depend on core.

**Strengths.** Strong visibility of feature boundaries; provider surface is isolated in its own crate; shared types are extracted into `*-types` crates so the public API is stable; feature flags keep binary size/configurable surface small.

**Weaknesses.** The core `goose` crate is large (single crate owns agent loop, session, scheduling, security, prompts, and provider registry) and approaches a monolith. Cross-cutting concerns such as `config::Config::global()` and `SessionStorage` statics create hidden dependencies.

**Reusable patterns.** Workspace-level feature flags; separate `*-types` crates for API stability; `provider-types` split is especially relevant for ACC's runtime provider interface.

**Does ACC solve this?** ACC already has `ai_command_center/domain/`, `runtime/providers/`, `repositories/`, and `services/`, but they are Python packages rather than crates and the public/package boundaries are less explicit.

**Is Goose objectively better?** The compile-time crate boundary is objectively stronger than Python's module boundary for enforcing dependency direction, but ACC's conceptual layering is comparable.

**Risks for ACC.** Adopting crate-style Python packages with strict `__init__.py` exports is low risk and would strengthen the existing architecture rather than replace it.

**Recommendation:** **Adapt** — formalize package-level ownership with public/private modules and an architecture lint (the repo already has `scripts/arch_lint.py`; extend it with package import rules).

---

## 2. Runtime

**Purpose.** Execution loop, async/event loop, task lifecycle, cancellation, timeouts, resource management.

**Implementation notes.** The CLI creates a multi-thread `tokio` runtime on a dedicated 8 MiB stack thread (`crates/goose-cli/src/main.rs`). `crates/goose/src/execution/manager.rs` owns the `AgentManager` — an `Arc`-wrapped manager with:

- `LruCache<String, Arc<Agent>>` for hot sessions
- `RwLock<HashMap<String, CancellationToken>>` for per-session cancellation
- `Mutex<HashMap<String, Arc<Mutex<()>>>>` per-session creation locks to prevent duplicate `initialize` calls on MCP servers under concurrent callers

The agent loop in `crates/goose/src/agents/agent.rs` is a stream-driven reactor: model completion yields a `BoxStream` of messages, tool calls are dispatched, and results are streamed back. `tokio_util::sync::CancellationToken` is used throughout. `tokio_cron_scheduler` is used in `scheduler.rs` for scheduled recipes. `tracing_futures::Instrument` attaches spans to async work.

**Strengths.** Per-session cancellation tokens, creation locks to avoid thundering herd, LRU for agent/session cache, explicit max-turn constants, and cron scheduling are all production-hardened patterns.

**Weaknesses.** The `AgentManager` is a global `OnceCell<Arc<AgentManager>>`; heavy use of `Arc<RwLock<...>>` can become a contention point; `tokio_cron_scheduler` is an external dependency with its own runtime expectations.

**Reusable patterns.** Per-session creation locks; cancellation-token-per-task; `LruCache` for bounded in-memory actor cache; cron-backed recipe scheduler.

**Does ACC solve this?** ACC has `BaseService` lifecycle, `EventBus` topics, and `ThreadPoolExecutor`. Cancellation is less explicit; session caching is repository-backed rather than in-memory LRU.

**Is Goose objectively better?** The explicit cancellation and session-creation locks are better than implicit Python futures. The `AgentManager` global is not better than ACC's service lifecycle framework.

**Risks for ACC.** Reusing "global manager" patterns violates ACC Rule 2 (no global state). Cancellation and LRU should be implemented inside `AppState` or a service, not as a module-level static.

**Recommendation:** **Adapt** — port `CancellationToken`-style cancellation and per-session creation locks into `BaseService`; add bounded in-memory caching to `AppState` for hot sessions. Do **not** adopt the `OnceCell` global manager pattern.

---

## 3. Provider Layer

**Purpose.** Provider abstraction, model adapters, streaming, tool calling, retries, fallback, token accounting.

**Implementation notes.** `goose-providers` defines a `Provider` trait and `ProviderDef` trait in `crates/goose/src/providers/base.rs`. `crates/goose/src/providers/provider_registry.rs` builds a `ProviderRegistry` from `ProviderDef` metadata and constructor closures. `crates/goose/src/providers/init.rs` registers ~25 providers behind the registry. `ProviderEntry` carries `ProviderMetadata`, `ProviderType` (Preferred/Builtin/Declarative/Custom), TLS config, and inventory resolvers that can refresh available models. Provider construction returns `Arc<dyn Provider>`. `goose_providers::model::ModelConfig` carries `model_name`, `context_limit`, `temperature`, `max_tokens`, `toolshim_model`, `thinking_effort`, `request_params`, and `request_headers`. `crates/goose/src/providers/retry.rs` (re-exported from `goose-providers`) implements `RetryConfig` with exponential backoff. `crates/goose/src/model_config.rs` materializes user config into a canonical `ModelConfig`, applies provider-specific defaults, and supports a `GOOSE_FAST_MODEL` path for lightweight tasks with fallback to the main model.

**Strengths.** Clean trait boundary; rich metadata per provider; declarative/custom providers can be added without changing core; model config normalization keeps provider quirks contained; retry and fast-model fallback are first-class; token usage tracking is part of the provider return (`ProviderUsage`).

**Weaknesses.** Provider registry is a static `OnceCell<RwLock<ProviderRegistry>>`; the provider surface is large and some adapters are thin wrappers over vendor SDKs.

**Reusable patterns.** `ProviderDef` + `ProviderRegistry` + constructor-closure registration; `ModelConfig` builder with provider-specific normalization; `get_fast_model` fast-path with fallback; `ProviderUsage` token/cost accounting attached to every completion.

**Does ACC solve this?** ACC has `ai_command_center/runtime/providers/` and `AgentRuntimeProvider` Protocol with `health`, `supports`, `invoke`. `CapabilityRouter` classifies capability kinds. It is conceptually similar but less rich in provider metadata and model-config normalization.

**Is Goose objectively better?** Goose's `ProviderDef` registration, metadata, and `ModelConfig` normalization are more mature for a multi-provider CLI. ACC's `RuntimeInvocationRequest` and `ContextBundle` are more focused on external sidecar integration.

**Risks for ACC.** Borrowing the registry pattern must not bypass `ContextManager` or `CapabilityRouter`. Providers must still be integrated through `AGENT_RUNTIME_INTERFACE.md`.

**Recommendation:** **Adapt** — extend ACC `runtime/providers/` with a `ProviderRegistry`, provider metadata, and `ModelConfig` normalization. Use this to improve `ModelRouterService` while preserving the `ContextManager` gate.

---

## 4. Extension System

**Purpose.** Plugin discovery, loading, sandboxing, capability registration, permissions, versioning, DI.

**Implementation notes.** Goose uses the Model Context Protocol (MCP) as its extension backbone. `crates/goose/src/agents/extension.rs` defines `ExtensionConfig` with variants `Stdio`, `Builtin`, `Sse` (deprecated), and platform-provided extensions. `agents/extension_manager.rs` initializes MCP clients over stdio/HTTP. `crates/goose/src/agents/platform_extensions/` contains built-in platform extensions. `Envs` validates a hard-coded deny-list of dangerous environment variables (PATH, LD_PRELOAD, DYLD_INSERT_LIBRARIES, NODE_OPTIONS, etc.) before passing them to an extension process. `crates/goose/src/config/extensions.rs` persists enabled extensions. `crates/goose/src/skills/` and `crates/goose/src/sources.rs` manage markdown-based skills/projects under `.agents/skills/` and `<dataDir>/projects/`. The ACP (`agent_client_protocol`) exposes custom JSON-RPC methods for source/skill/agent CRUD.

**Strengths.** MCP is an open standard; extension env-var deny-list is a strong security primitive; skills/projects as markdown frontmatter is human-editable; platform extensions are first-class; ACP creates a stable host/sidecar contract.

**Weaknesses.** MCP stdio processes are external subprocesses with lifecycle complexity; SSE transport is deprecated; sandboxing is limited to env var filtering. There is no fine-grained permission grant per extension beyond tool-level permissions.

**Reusable patterns.** Env-var deny-list for spawned tools/extensions; markdown frontmatter for user-editable skills/projects; ACP custom method contract for host↔extension source management.

**Does ACC solve this?** ACC has `PluginRegistryService`, `runtime/providers/`, and YAML manifests under `plugins/manifests/`. ACC does not yet use MCP; extensions are native Python plugins or future sidecars.

**Is Goose objectively better?** MCP ecosystem breadth is better. ACC's explicit plugin manifest and goal-scheduler integration is better for agentic workflows.

**Risks for ACC.** Adopting MCP as the primary extension model could create shadow state if an MCP server writes files or settings directly. Invariant 13 requires ACC to remain the system of record.

**Recommendation:** **Adapt** — add an MCP runtime provider/adapter in `ai_command_center/runtime/providers/mcp_provider.py` that treats MCP servers as capability sources, executes tools through ACC `ToolExecutorService`, and never lets an MCP server become canonical state. Reuse the env-var deny-list wholesale.

---

## 5. Tool Execution

**Purpose.** Tool lifecycle, validation, argument handling, errors, receipts, timeouts, retries, security.

**Implementation notes.** The tool loop lives in `crates/goose/src/agents/agent.rs` and `crates/goose/src/agents/tool_execution.rs`. `ToolCallContext` carries `session_id`, `working_dir`, and `tool_call_request_id`. `ToolCallResult` returns a future plus optional notification/action-required streams. `ToolConfirmationRouter` registers pending confirmations and waits on a oneshot channel. `crates/goose/src/tool_inspection.rs` defines an inspection framework (`ToolInspector` trait) and `ToolInspectionManager` that runs multiple inspectors (security, repetition) before execution. `crates/goose/src/tool_monitor.rs` implements `RepetitionInspector` with call-count and repeated-argument detection. `crates/goose/src/permission/` has `PermissionManager`, `PermissionLevel` (AlwaysAllow, AllowOnce, Ask, NeverAllow), and `PermissionStore` backed by config. `crates/goose/src/security/` contains `SecurityManager`, prompt-injection scanning, `AdversaryInspector`, `EgressInspector`, and a `PromptInjectionScanner` with optional ML classification. Tool responses are wrapped in `rmcp::model::CallToolResult` with `Content` variants.

**Strengths.** Multi-stage inspection pipeline before tool dispatch; explicit permission levels with persistence; repetition guardrails; security scanner with pattern + optional ML; action-required messages for user confirmation; cancellation tokens passed into tool calls.

**Weaknesses.** Inspections and permission checks are synchronous in the agent loop; security scanner can fall back silently to pattern-only; tool errors are not always surfaced as structured "receipts" with evidence.

**Reusable patterns.** `ToolInspector` pluggable pipeline; `ToolCallContext` request context; `PermissionLevel` enum; `RepetitionInspector`; `SecurityManager` with configurable thresholds; action-required messages for human-in-the-loop.

**Does ACC solve this?** ACC has `ToolExecutorService`, `ToolRegistry`, `ToolExecution` domain model, and planned `PermissionService`. The inspection pipeline is less developed.

**Is Goose objectively better?** Yes for tool guardrails, security scanning, and permission levels. ACC's receipt system is more explicit for evidence collection.

**Risks for ACC.** Integrating Goose's inspection pipeline into ACC must route through `EventBus` topics (`tool.started`, `tool.completed`, `tool.failed`) and store results in `ToolExecution`/`Receipt` domain models, not inside the agent object.

**Recommendation:** **Adapt** — add `ToolInspector` hooks to `ToolExecutorService`; implement `PermissionLevel` and `RepetitionInspector`; wire security scan findings as `telemetry.event` and `tool.failed` events.

---

## 6. State Management

**Purpose.** Conversation state, workspace state, memory, cache, session, graph, history.

**Implementation notes.** `crates/goose/src/session/session_manager.rs` defines the `Session` struct and `SessionManager` backed by SQLite (`sqlx`, `sessions.db`, schema version 15). `Session` contains `id`, `working_dir`, `name`, `session_type`, `created_at`, `updated_at`, `extension_data`, `usage`, `accumulated_usage/cost`, `schedule_id`, `recipe`, `user_recipe_values`, `conversation` (a `Conversation` with messages), `message_count`, `provider_name`, `model_config`, `goose_mode`, `archived_at`, `project_id`, `parent_session_id`, and `last_message_snippet`. `SessionUpdateBuilder` provides incremental updates. `SessionStorage` is a global `LazyLock`. `crates/goose/src/session/extension_data.rs` tracks enabled extensions and per-extension state (`TodoState`). `crates/goose/src/context_mgmt/mod.rs` compacts conversations by summarizing older messages and setting visibility metadata so the model only sees the summary.

**Strengths.** Rich session model; schema versioning; incremental update builder; token/cost accumulation per session; conversation compaction with visibility metadata; extension state captured in session.

**Weaknesses.** `SessionStorage` is a module-level static (`LazyLock`); `SessionManager` is `Arc`-held inside `AgentConfig` rather than an actor; no evidence graph or world model integration beyond the conversation object.

**Reusable patterns.** `SessionUpdateBuilder`; accumulated usage/cost fields; schema-versioned SQLite; conversation compaction with agent/user visibility metadata; per-session extension state.

**Does ACC solve this?** ACC has `AppState`, `SessionService`, repositories for conversation/notes/memory/settings/telemetry, and a World Model graph. Domain models are more granular (`conversation.py`, `memory_item.py`, `note.py`, `service_state.py`, `telemetry_event.py`).

**Is Goose objectively better?** Goose's compaction/visibility metadata and usage accumulation are more advanced. ACC's repository/EventBus separation is architecturally cleaner.

**Risks for ACC.** Do not import the `LazyLock` global storage. The compaction and `SessionUpdateBuilder` patterns can be implemented inside `SessionService` and `ConversationRepository`.

**Recommendation:** **Adapt** — add conversation compaction with visibility metadata to `ConversationRepository`; add usage/cost accumulation to `SessionService`; port `SessionUpdateBuilder` semantics to `AppState` reducers.

---

## 7. Context Assembly

**Purpose.** Prompt construction, memory injection, tool descriptions, context pruning, retrieval, provider-specific prompts.

**Implementation notes.** `crates/goose/src/context_mgmt/mod.rs` is the primary context manager. It checks `check_if_compaction_needed` against a default threshold of 0.8, calls `compact_messages` to summarize older turns, and produces a `CompactionResult` with retained token count and `ProviderUsage`. It preserves the most recent text-only user message and injects a continuation instruction telling the model not to mention the summary. `crates/goose/src/token_counter.rs` counts chat/tool tokens using `tiktoken-rs` with an LRU cache keyed by `blake3` hash. `crates/goose/src/sources.rs` handles filesystem-backed CRUD for `SourceEntry` values (skills, projects, agents). `crates/goose/src/prompts/` and `crates/goose/src/prompt_template.rs` use `minijinja` templates. `crates/goose/src/agents/prompt_manager.rs` assembles system and user prompts. `model_config.rs` supports `GOOSE_FAST_MODEL` for cheap summarization.

**Strengths.** Compaction is automatic and transparent to the user; token counting is cached and tool-aware; prompt templates are Jinja-based; skills/projects are first-class source types; fast model offloads summarization.

**Weaknesses.** Compaction is lossy and relies on a single summary message; no semantic retrieval from memory graph; `Context` is not a strongly typed bundle like ACC's planned `ContextBundle`.

**Reusable patterns.** Token-counting LRU with `blake3` key; automatic compaction with continuation prompt; `minijinja` templating; fast-model fallback for summarization; source entries with markdown frontmatter.

**Does ACC solve this?** ACC has `capability_context_assembler.py` and `ContextBundle` in `AGENT_RUNTIME_INTERFACE.md`. It is less advanced in automatic compaction and token caching.

**Is Goose objectively better?** Yes for token counting efficiency and automatic compaction. ACC's typed `ContextBundle` is stronger for external runtime contracts.

**Risks for ACC.** Context assembly must remain owned by `ContextManager` and results published as `system.snapshot` / `conversation.updated`. Compaction should not bypass the World Model or repository layer.

**Recommendation:** **Adapt** — add token-count LRU and automatic conversation compaction to `ContextManager`; use `TelemetryService` to emit compaction events; integrate `minijinja` or equivalent for prompt templates.

---

## 8. Desktop Architecture

**Purpose.** UI architecture, windowing, command palette, settings, notifications, tray, updates, hotkeys, startup, performance.

**Implementation notes.** `ui/desktop` is an Electron Forge + Vite + React + TypeScript app. It uses Radix UI, TailwindCSS v4, Framer Motion, `react-intl` for i18n, `lucide-react` icons, `react-toastify` notifications, `zod` validation, and `electron-window-state` for window persistence. `main.ts` is the Electron main process. `preload.ts` exposes a controlled IPC bridge. `renderer.tsx` mounts the React app. `gooseServe.ts` talks to the local Rust backend over HTTP. `backendStatus.ts` monitors backend health. `recipe/` UI supports recipe/deeplink workflows. Playwright is used for e2e; Vitest for unit/integration. `forge.config.ts` packages for macOS, Windows, Linux (deb/rpm/flatpak/squirrel/zip). `i18n/` uses FormatJS with extract/compile scripts.

**Strengths.** Modern React stack; strong i18n pipeline; controlled preload bridge reduces exposed surface; cross-platform packaging matrix; Playwright e2e; backend status UI.

**Weaknesses.** Electron bundles Chromium and Node, increasing install size; the main process is large (98 KB `main.ts`); UI state is partly managed through Electron IPC and local HTTP rather than a single event bus.

**Reusable patterns.** i18n extract/compile pipeline; backend status indicator; preload IPC bridge; cross-platform Forge packaging; Playwright + Vitest dual test stack.

**Does ACC solve this?** ACC uses CustomTkinter. `ACC_UI_REFURBISHMENT.md` and `UI_REFURBISHMENT_BACKLOG.md` plan a modern web-based UI but this is future work.

**Is Goose objectively better?** Yes for UX richness, i18n, and packaging. ACC's state-driven architecture is better for separating UI from business logic.

**Risks for ACC.** A future web UI must still be a "renderer only" that reads `AppState` and publishes `UI_*` events. It must not access files, SQLite, Ollama, or services directly.

**Recommendation:** **Future consideration** — when ACC refurbishes the UI, use Goose's Electron/Vite/React/i18n/packaging stack as a reference implementation, but keep the `UI → AppState → EventBus → Services` contract. Do not adopt before Phase 11+ UI work is planned.

---

## 9. Configuration

**Purpose.** Profiles, provider config, workspace config, secrets, env vars, defaults, migration, validation.

**Implementation notes.** `crates/goose/src/config/base.rs` implements a `Config` singleton backed by YAML with precedence: env vars → user config (`~/.config/goose/config.yaml`) and optional additional config files → system config (`/etc/goose/config.yaml` or `C:\ProgramData\goose\config.yaml`). Secrets are loaded from the system keyring by default; if keyring is disabled they fall back to a `secrets.yaml` file with 0o600 permissions. `Config` uses a `Mutex<()>` guard to serialize writes and a `secrets_cache`. `crates/goose/src/config/paths.rs` uses `etcetera` for cross-platform directories and supports `GOOSE_PATH_ROOT` to relocate config/data/state/plugins. `crates/goose/src/config/migrations.rs` migrates legacy flat provider keys into a structured `providers:` block and platform extensions into the `extensions:` block. `crates/goose/src/config/providers.rs` and `crates/goose/src/config/declarative_providers.rs` manage provider entries and custom provider YAML definitions. `ExperimentManager` toggles experiments.

**Strengths.** Cross-platform path resolution; env var override with UPPERCASE conversion; keyring-first secrets with file fallback; structured provider config; migrations preserve user data; `GOOSE_PATH_ROOT` makes the install portable and testable.

**Weaknesses.** `Config` is a global `OnceCell` singleton, which hinders testing and multi-tenant use; secrets cache is `Mutex<Option<HashMap>>` rather than a typed snapshot; migrations are ad-hoc functions rather than a version-driven framework.

**Reusable patterns.** `etcetera`-based path strategy plus `GOOSE_PATH_ROOT`; env > user > system config precedence; keyring-first secrets; migration from flat to structured config; declarative provider YAML files.

**Does ACC solve this?** ACC has `SettingsSnapshot`, `settings_schema.py`, `settings_service.py`, `settings_repository.py`, and `migration_manager.py`. The conceptual coverage is similar but the implementation is newer and explicitly forbids global state.

**Is Goose objectively better?** Goose's cross-platform path handling and keyring integration are more battle-tested. ACC's `SettingsSnapshot` / schema / repository separation is architecturally cleaner.

**Risks for ACC.** Do not introduce a `Config::global()` singleton. Use `SettingsService` to produce `SettingsSnapshot` and `SettingsRepository` for persistence.

**Recommendation:** **Adapt** — integrate `etcetera`/path strategy into `settings_service.py`; add keyring-backed secret storage to `settings_repository.py`; strengthen `migration_manager.py` with version-driven migration functions inspired by Goose's provider/extension migrations.

---

## 10. Logging & Observability

**Purpose.** Structured logging, metrics, telemetry, tracing, execution history, diagnostics, crash recovery.

**Implementation notes.** `crates/goose/src/logging.rs` builds a `tracing_subscriber` with file + optional console layers, JSON or plain formatting, per-component log directories, date-based subdirectories, and automatic cleanup of logs older than two weeks. `RUST_LOG` overrides defaults. `crates/goose/src/tracing/observation_layer.rs` and `langfuse_layer.rs` convert `tracing` spans/events into Langfuse observation batches (traces/spans). `crates/goose/src/otel/otlp.rs` initializes OpenTelemetry traces, metrics, and logs exporters over HTTP/protobuf, with a dedicated single-thread Tokio runtime because OTel batch processors run in raw threads. `posthog.rs` sends product telemetry. `crates/goose/src/session/diagnostics.rs` and `doctor.rs` collect system info, recent logs, config paths, and extension status into a diagnostics report.

**Strengths.** Layered `tracing` subscriber; per-component rotated logs; JSON logging for machine parsing; OTel + Langfuse + PostHog are all optional feature flags; dedicated OTel runtime solves a common integration footgun; diagnostics report lowers support burden.

**Weaknesses.** Multiple telemetry sinks are configured separately and may double-emit; OTel setup is complex and feature-flagged; Langfuse layer is tightly coupled to `tracing` internals.

**Reusable patterns.** Per-component rolling log directory with retention; `tracing` structured events with `tracing-appender`; OTel HTTP export with a dedicated runtime; diagnostics module that gathers config, logs, and system info.

**Does ACC solve this?** ACC has `TelemetryService`, `telemetry_event.py` domain model, and `EventBus` `telemetry.event` topic. Logging is Python standard logging. No OTel or Langfuse integration yet.

**Is Goose objectively better?** Yes for structured/rotated logs, OTel, and diagnostics. ACC's event-based telemetry is better for authority-chain decoupling.

**Risks for ACC.** OTel/Langfuse must not leak secrets or raw conversation content. Telemetry events should be emitted through `TelemetryService` and `EventBus`.

**Recommendation:** **Adapt** — implement `TelemetryService` sinks for structured file logs with rotation and retention; add optional OTel and Langfuse exporters gated by settings; add a `doctor`/`diagnostics` command that collects `SystemSnapshot` and recent telemetry.

---

## 11. Testing

**Purpose.** Unit/integration/architecture tests, mocking, CI, coverage.

**Implementation notes.** Tests live in three places: inline `#[cfg(test)]` modules in source files (e.g., `mcp_utils.rs`, `config/base.rs`, `logging.rs`), `crates/goose/tests/`, and `crates/goose-cli/tests/`. `goose-test` and `goose-test-support` crates share test helpers. `wiremock` is used for HTTP mocking. `tempfile` for temp dirs. `test-case` for parameterized tests. `serial_test` for serializing tests that touch global state. `ui/desktop` uses Vitest for unit/integration and Playwright for e2e. `.github/workflows/` runs the full matrix. `deny.toml` audits dependencies. `clippy.toml` and workspace lints enforce style. `goose-self-test.yaml` is a self-test recipe. `evals/` contains evaluation harnesses.

**Strengths.** Inline tests next to implementation; shared test crates; HTTP mocking for providers; serial test annotations; e2e coverage for the desktop; dependency/license auditing.

**Weaknesses.** Heavy reliance on inline tests can bloat source files; global `Config` / `SessionStorage` statics force `serial_test` annotations; e2e tests depend on a live backend.

**Reusable patterns.** Inline `#[cfg(test)]` modules for unit tests adjacent to code; shared `test-support` package; `wiremock` for provider HTTP mocking; Playwright + Vitest for desktop; `deny.toml` license audit.

**Does ACC solve this?** ACC has `pytest`, `conftest.py`, `tests/` with 120+ files, `arch_lint.py`, `bandit`, and `coverage`. It already has strong governance gating.

**Is Goose objectively better?** No — ACC's test suite is already extensive. Goose's `deny.toml` and `arch_lint` equivalents are useful additions.

**Risks for ACC.** Adopting Rust-style inline tests in Python is not idiomatic. Instead, strengthen existing `scripts/arch_lint.py` and add a license-dependency audit.

**Recommendation:** **Adapt** — add a `tests/support/` package for shared fixtures if not present; add license/dependency audit step to CI; ensure provider tests are mockable (ACC already uses `StubOllamaService` — extend this pattern).

---

## 12. Performance

**Purpose.** Lazy loading, startup optimization, caching, async execution, parallelism, memory management.

**Implementation notes.** `tokio` multi-thread runtime handles async I/O. `rayon` is used for data parallelism (declared in workspace deps and used in tree-sitter/local inference code). `lru` caches provider model metadata and token counts. `OnceCell` and `LazyLock` defer initialization of tokenizer, global config, and session storage. `tiktoken-rs` token counting is cached with `blake3`-hashed keys. `fs-err` gives clearer file errors. The `AgentManager` keeps an LRU of hot agents and uses per-session creation locks. `candle` local inference is feature-flagged.

**Strengths.** Async-by-default with explicit cancellation; LRU for token and agent caching; lazy statics for expensive startup; `rayon` for CPU-bound work; feature flags keep optional heavy deps out of base builds.

**Weaknesses.** `OnceCell`/`LazyLock` globals are lazy but remain global state; `rayon` is only beneficial when work is CPU-bound; LRU cache sizing is not configurable in the inspected code.

**Reusable patterns.** LRU token cache; lazy tokenizer initialization; per-session creation locks; async provider completions with `BoxStream`; feature flags for heavy dependencies.

**Does ACC solve this?** ACC uses `ThreadPoolExecutor`, `functools.lru_cache`, and lazy imports. It lacks explicit cancellation tokens and `SettingsSnapshot` is loaded at startup.

**Is Goose objectively better?** Yes for cancellation, token cache, and feature-gated builds. ACC's `AppState` snapshot model is better for UI responsiveness.

**Risks for ACC.** Do not implement `OnceCell` globals. Use `AppState` caches and repository-level memoization. Cancellation should be built into `ToolExecutorService` and `BaseService`.

**Recommendation:** **Adapt** — add a token-counting cache to `ContextManager`; add explicit cancellation support to `BaseService` lifecycle and `ToolExecutorService`; use `functools.lru_cache` or a typed cache service for provider metadata.

---

# Final Report: A / B / C / D

## A — Excellent Engineering Worth Borrowing

These patterns are concrete, low-risk, and can be adopted almost immediately inside ACC's existing ownership layers.

1. **Per-tool/per-call cancellation tokens.** Wire `CancellationToken` semantics into `BaseService` and `ToolExecutorService`. Publish `tool.started`, `tool.completed`, `tool.failed` on `EventBus`.
2. **Token-counting LRU with content hash key.** Implement in `ContextManager` or a new `TokenCounterService`; emit `telemetry.event` for cache hits/misses.
3. **Extension env-var deny-list.** Port the 31-key deny-list from `crates/goose/src/agents/extension.rs` to any process-spawning tool (local command runner, MCP adapter, QwenPaw sidecar spawn).
4. **Per-session creation locks.** Use in `SessionService` to prevent duplicate sidecar/MCP initialization under concurrent UI/chat requests.
5. **Structured file logging with retention.** Extend `TelemetryService` to write JSON/plain logs per component with 14-day cleanup.
6. **`GOOSE_FAST_MODEL` fast-path with fallback.** Generalize to `ContextManager.complete_fast()` for summarization, session naming, and cheap classification.
7. **Diagnostics module.** Collect `SystemSnapshot`, recent logs, settings, and service health into a single diagnostics bundle.
8. **Keyring-first secrets with file fallback.** Add to `SettingsRepository` for API keys.
9. **Cross-platform path strategy with `etcetera` equivalent.** Standardize `settings_path()` / `data_path()` / `state_path()` in `SettingsService`.
10. **`ToolInspector` plugin pipeline.** Add pre-execution inspection hooks to `ToolExecutorService` (repetition, security, egress).

## B — Useful Ideas That Need Adaptation

These are strong ideas but must be reshaped to fit ACC's state-driven, EventBus-governed architecture.

1. **MCP extension system.** Build `ai_command_center/runtime/providers/mcp_provider.py` that wraps MCP servers. Tools must execute through `ToolExecutorService` and results returned via `EventBus` so ACC remains the system of record.
2. **Provider registry with metadata and constructor closures.** Add to `runtime/providers/` but ensure `ContextManager` still assembles all context and `CapabilityRouter` selects the provider.
3. **Automatic conversation compaction with visibility metadata.** Add to `ConversationRepository`/`ContextManager`; use `AppState` to project compacted snapshots to UI.
4. **Scheduled recipes / cron jobs.** Port to `GoalScheduler` once it supports recurring goals; store schedules in `GoalRepository` and trigger via `EventBus`.
5. **`ModelConfig` builder with provider normalization.** Extend `SettingsSnapshot` or add a `ModelConfig` domain model; keep provider quirks inside adapters.
6. **Markdown frontmatter skills/projects.** Add to `NotesRepository`/`MemoryRepository` as structured source entries; use `Note` domain model.
7. **Security scanner with pattern + optional ML classification.** Add to `PermissionService` / `ToolExecutorService`; emit `security.finding` telemetry events.
8. **Electron/Vite/React desktop UI.** Use only when ACC begins UI refurbishment; must still read from `AppState` and publish `UI_*` events.
9. **OTel/Langfuse telemetry sinks.** Add behind `telemetry.enabled` settings; ensure no raw secrets or conversation content is exported.
10. **Provider `GOOSE_FAST_MODEL` and fallback.** Generalize as `CapabilityRouter` tier-1 cheap model selection.

## C — Architectural Differences

These areas intentionally diverge; do not copy them blindly.

1. **Rust vs Python stack.** ACC is Python. Adopt patterns, not crates.
2. **MCP as primary extension model.** Goose is MCP-native. ACC is authority-chain native with MCP as an optional runtime provider. Do not let MCP servers own state.
3. **Global `Config` / `SessionStorage` statics (`OnceCell` / `LazyLock`).** ACC Rule 2 forbids global state. Use `AppState` and repository instances.
4. **Direct service references (`AgentConfig` holds `Arc<SessionManager>`, etc.).** ACC Rule 3 forbids direct service-to-service calls. Use `EventBus` topics.
5. **Electron IPC/local HTTP for UI state.** ACC's UI must be renderer-only; Electron desktop can be adopted later but must be wired through `AppState`/`EventBus`.
6. **SQLite as direct session store in core.** ACC uses repositories. Keep `SQLite` behind repository boundaries.
7. **Provider registry as global static.** ACC must use `CapabilityRouter` / `RuntimeProvider` instances managed through `BaseService` lifecycle.
8. **`anyhow` / `thiserror` error propagation.** ACC uses typed domain exceptions (`ToolExecution`, `ServiceState`, etc.). Keep typed errors.
9. **Goose `GooseMode` (chat vs autonomous).** ACC will express autonomy through `GoalScheduler` and `PermissionService`, not a single mode enum.
10. **Tree-sitter / candle local inference in core.** Heavy optional deps must be isolated behind runtime providers or plugins, not core.

## D — Integration Roadmap

### Quick wins (low effort, low risk, immediate impact)

| # | Item | Owner | Acceptance |
|---|------|-------|------------|
| 1 | Port env-var deny-list to process-spawning tools | `ToolExecutorService` | Unit test covering PATH/LD_PRELOAD rejection |
| 2 | Add token-counting LRU to `ContextManager` | `ContextManager` / new `TokenCounterService` | Cache hit/miss telemetry; unit tests for tool token counts |
| 3 | Implement per-session creation locks in `SessionService` | `SessionService` | Concurrent create-agent calls deduplicated |
| 4 | Add structured file logging with rotation/retention to `TelemetryService` | `TelemetryService` | Logs land under state/logs/<component> with 14-day cleanup |
| 5 | Add `ToolInspector` repetition guard hook | `ToolExecutorService` | Repeated identical tool calls trigger `tool.failed` |
| 6 | Add keyring-first secrets to `SettingsRepository` | `SettingsRepository` | API keys stored in OS keyring, fallback to encrypted file |

### Medium projects (weeks, moderate risk, high value)

| # | Item | Owner | Acceptance |
|---|------|-------|------------|
| 1 | `ProviderRegistry` with metadata and `ModelConfig` normalization | `runtime/providers/` | New providers can be registered without touching `ModelRouterService` internals |
| 2 | Conversation compaction with visibility metadata | `ConversationRepository` + `ContextManager` | Long sessions compact automatically; UI still sees full history via `AppState` projection |
| 3 | `ToolInspector` pipeline (security, egress, repetition) | `ToolExecutorService` + `PermissionService` | Pluggable inspectors run before every tool call |
| 4 | MCP runtime provider adapter | `runtime/providers/mcp_provider.py` | MCP tools execute through `ToolExecutorService`; no direct MCP→SQLite writes |
| 5 | `complete_fast()` cheap model path for summarization/classification | `ContextManager` | Falls back to main model on failure |
| 6 | Cross-platform path strategy in `SettingsService` | `SettingsService` | `APPDATA`/XDG/macOS paths resolved consistently; `AICC_PATH_ROOT` override supported |

### Major investments (months, higher risk, strategic)

| # | Item | Owner | Acceptance |
|---|------|-------|------------|
| 1 | Electron/Vite/React UI refurbishment | `ui/` future track | UI is renderer-only, reads `AppState`, publishes `UI_*` events, no direct service calls |
| 2 | OTel + Langfuse telemetry sinks | `TelemetryService` | Optional sinks behind settings; no secret leakage |
| 3 | Local inference runtime provider (candle/ONNX/llama-cpp) | `runtime/providers/` | Local model runs as optional provider, not core dependency |
| 4 | Scheduled goal/recipe execution in `GoalScheduler` | `GoalScheduler` | Cron-style recurring goals persisted through `GoalRepository` |
| 5 | Security scanner with ML classification | `PermissionService` | Configurable prompt/command injection scanner with fallback |
| 6 | Full diagnostics bundle (`doctor`) | `SystemSnapshot` + `TelemetryService` | One-command report of settings, logs, service health, and workspace state |

---

## Summary

Goose is a mature, multi-provider, MCP-native agent runtime with excellent patterns for provider abstraction, tool guardrails, context compaction, logging/observability, and cross-platform packaging. ACC's authority-chain, state-driven, EventBus-governed architecture is conceptually stronger for ownership and governance, but it can directly borrow many tactical engineering patterns from Goose.

The highest-value, lowest-risk adoptions are: cancellation tokens, token-count caching, env-var deny-lists, per-session creation locks, `ToolInspector` hooks, structured logging with retention, keyring-first secrets, `ProviderRegistry` metadata, and `ModelConfig`/fast-model normalization. The highest-risk misstep would be copying Goose's global `Config`/`SessionStorage` statics or direct service references, which violate ACC Rules 2 and 3.

The recommended path is to treat Goose as a **pattern library**, not a replacement, and to integrate each borrowed pattern through the existing `UI → AppState → EventBus → Services → Repositories → Storage` ownership chain.
