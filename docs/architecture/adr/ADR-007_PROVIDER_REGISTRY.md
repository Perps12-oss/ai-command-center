# ADR-007: Provider Registry Snapshot in AppState

**Status:** Proposed  
**Date:** 2026-07-27  
**Deciders:** Architecture Review (Tom)  
**Supersedes:** —  
**Related:** `research/patterns/PAT-001.md`, `research/integration/INT-001.md`, `research/decisions/RD-001.md`, `docs/architecture/MODEL_ORCHESTRATION.md`, `docs/architecture/AGENT_RUNTIME_INTERFACE.md`

---

## Context

ACC currently routes model requests through `ModelRouterService` and executes them via `OllamaHttpService` and `OpenAIHttpService`. Provider metadata (name, supported models, required config keys, configured state) is scattered across service code and settings, so the UI cannot render a provider catalog without constructing heavy client objects. `block/goose` uses a `ProviderRegistry` of `ProviderEntry` objects with inventory resolvers to decouple discovery from instantiation.

## Decision

Maintain a **ProviderRegistry** service that publishes a read-only `ProviderRegistrySnapshot` into `AppState`. The registry is the **catalog authority**; `ModelRouterService` remains the **execution authority** for selecting and invoking providers.

### Contract

- `provider.discovered` — registry publishes the full catalog after startup or when a custom provider file changes.
- `provider.configured` — emitted when required secrets/settings are present for a provider.
- `provider.changed` — emitted when a provider entry is added, removed, or updated.
- `provider.select` — UI publishes user intent to change the active provider; `SettingsService` persists the choice and emits `settings.updated`.
- `ProviderRegistrySnapshot` contains metadata, default model, known models, config keys, provider type, and `configured`/`available` flags.

## Rationale

| Factor | Without registry | With registry |
|--------|-----------------|---------------|
| UI provider picker | Reaches into settings/service code | Reads `AppState` snapshot |
| Custom providers | Requires code changes | Loaded from JSON into registry |
| Execution authority | `ModelRouterService` + ad-hoc provider strings | `ModelRouterService` uses registry catalog plus runtime contract |
| Testability | Providers instantiated to inspect metadata | Inventory resolvers check metadata/config only |

The registry does not replace `AgentRuntimeProvider` or `ModelRouterService`; it feeds them a catalog and a user-facing configuration model.

## Consequences

### Positive

- UI can render provider catalog without constructing clients.
- Custom providers become configuration rather than code.
- Provider lifecycle (metadata, refresh, cleanup hooks) is centralized.

### Negative / Risk

- Risk of registry becoming execution authority if it exposes `invoke` or `complete`. **Guarded:** registry has no execution methods.
- Risk of stale configuration state. **Mitigated:** registry subscribes to `settings.updated` and re-emits `provider.configured`.

## Implementation Notes

- Add `ai_command_center/core/ai/provider_registry.py`.
- `ProviderRegistry` is a `BaseService` with lifecycle states.
- `ProviderRegistrySnapshot` is a dataclass in `ai_command_center/domain/`.
- Custom provider JSON lives in `APPDATA/AICommandCenter/providers/` and is ignored by version control.

## Verification

- Unit test: registry publishes snapshot after `service.ready`.
- UI test: provider picker renders from `AppState` only.
- Architecture lint: no service calls `ProviderRegistry` for model execution.
