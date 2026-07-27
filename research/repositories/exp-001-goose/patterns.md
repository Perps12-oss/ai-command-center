# Pattern Candidates from block/goose

This file contains raw pattern candidates extracted from the expedition. Validated candidates are promoted to `research/patterns/PAT-NNN.md`.

## PC-001: Declarative Provider Registry with Inventory State

- **Problem:** A desktop agent must support many LLM providers, each with different auth, model catalogs, and configuration. The UI needs to know which providers are configured without constructing each provider.
- **Solution in Goose:**
  - `ProviderDef` trait maps provider metadata to a constructor.
  - `ProviderRegistry` stores `ProviderEntry` values keyed by name.
  - Each entry has `metadata`, `inventory_identity` resolver, `inventory_configured` resolver, `provider_type`, and `cleanup`.
  - Declarative custom providers are loaded from JSON and registered with a generic OpenAI-compatible constructor.
- **Initial assessment:** High reuse potential; ACC has a provider layer but could benefit from a registry + inventory abstraction.

## PC-002: MCP Extension Manager with Multi-Transport

- **Problem:** Tools come from many sources (local scripts, HTTP servers, bundled code, inline Python). The agent needs a uniform way to discover, connect, and invoke them.
- **Solution in Goose:**
  - `ExtensionConfig` enum supports stdio, streamable HTTP, Unix socket, builtin, platform, frontend, and inline Python.
  - `ExtensionManager` spawns child processes or HTTP clients, caches tool lists, and routes tool calls.
  - Environment variable filtering (`Envs`) blocks sensitive keys like PATH and LD_PRELOAD.
  - `env_keys` resolve secrets from a central config/keyring.
- **Initial assessment:** Relevant for ACC tool runtime, but the subprocess model conflicts with ACC's EventBus/service architecture. Adaptation required.

## PC-003: Conversation Context Compaction with Visibility Metadata

- **Problem:** Long conversations exceed model context windows. Summarization must preserve user-visible content while giving the model a compact history.
- **Solution in Goose:**
  - `context_mgmt::compact_messages` detects threshold exceedance and summarizes messages.
  - Original messages become `user_visible` but `agent_invisible`; the summary is `agent_visible` but not `user_visible`.
  - `format_message_for_compacting` serializes tool pairs into summarizable text.
  - `apply_structured_summary` renders a structured model response into a readable summary.
- **Initial assessment:** Strong fit for ACC conversation/memory management.

## PC-004: Tool Inspector / Confirmation Router Pipeline

- **Problem:** Tool calls from an LLM can be destructive, exfiltrate data, or repeat. The agent needs a pluggable inspection and approval pipeline.
- **Solution in Goose:**
  - `ToolInspectionManager` runs Security, Egress, Adversary, Permission, and Repetition inspectors.
  - `ToolConfirmationRouter` registers each tool request and waits for user confirmation.
  - `PermissionManager` stores allow/once/always/never rules per tool.
  - `handle_approval_tool_requests` dispatches approved tools and writes declined responses.
- **Initial assessment:** Strong fit for ACC execution authority and tool governance.

## PC-005: SQLite Session Storage with Schema Migrations

- **Problem:** Session data (messages, usage, recipes, extension state) must persist reliably across runs and support future schema changes.
- **Solution in Goose:**
  - `SessionStorage` uses sqlx + SQLite with WAL, `BEGIN IMMEDIATE`, and `CURRENT_SCHEMA_VERSION`.
  - Lazy pool initialization; migrations run once.
  - `SessionUpdateBuilder` provides typed, partial updates.
- **Initial assessment:** Overlaps ACC's repository pattern; useful as a reference but not a primary target.

## PC-006: Modular Tool Inspection and Permission Pipeline

- **Problem:** Tool calls can be destructive, leak data, or repeat. A pluggable inspection and approval pipeline is needed.
- **Solution in Goose:**
  - `ToolInspectionManager` runs Security, Egress, Adversary, Permission, and Repetition inspectors.
  - Each inspector returns an `InspectionResult` with `Allow`, `RequireApproval`, or `Block`.
  - `PermissionManager` persists per-tool `PermissionLevel` (`AlwaysAllow`, `AllowOnce`, `Ask`, `NeverAllow`).
- **Initial assessment:** Strong fit for ACC tool execution authority and runtime approval model.

## PC-007: Layered Telemetry with Pluggable Backends

- **Problem:** A single telemetry sink does not fit all deployments; local logs, OpenTelemetry, PostHog, and Langfuse are useful in different contexts.
- **Solution in Goose:**
  - `tracing` with `tracing-subscriber` layers for console, file, JSON, and optional OpenTelemetry.
  - Telemetry features are gated behind Cargo feature flags.
  - Security findings are emitted as structured tracing events.
- **Initial assessment:** Strong fit for ACC telemetry service; can subscribe to `telemetry.event` on EventBus.
