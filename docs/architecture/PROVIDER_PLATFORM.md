# Provider Capability Platform

Four-week delivery cycle for ACC provider SDK, observability, diagnostics, and certification.

## Architecture

```text
UI (Runtime Inspector)
  → AppState
  → EventBus
  → Services (Orchestration, Tracing, ExecutionRun, CapabilityLifecycle)
  → Repositories
  → SQLite / manifests
```

External runtimes integrate only through manifests and the Agent Runtime Interface (`docs/architecture/AGENT_RUNTIME_INTERFACE.md`). ACC remains system of record.

## Checkpoint: CP1 — FoundationBeta

**Status:** Baseline delivered before control-plane hardening (Provider Platform v2 immediate slice).

| Area | In place | Gaps (pre-CP2) |
|------|----------|----------------|
| Provider SDK | Manifest validation, certification CLI, adapters | Unified lifecycle registry |
| Observability | `TracingService` bus→OTel mapping | Settings-driven OTLP wiring |
| Diagnostics | Runtime Inspector 2.0, `provider_health_map`, execution runs | Capability lifecycle projection |
| Manifests | Extended runtime/orchestration manifests, six certification badges | Lifecycle state machine |
| Control plane | Event topics for orchestration + capability runtime | `CapabilityLifecycleManager`, lifecycle snapshot topic |

CP1 covers Weeks 1–4 of the original platform cycle (SDK, tracing, inspector, manifests). Lifecycle primitives and a thin control-plane manager are the CP2 entry work.

## Checkpoint: CP2 — ControlPlaneReady

**Status:** Immediate implementation slice — lifecycle contracts, manager, settings→tracing, CI lifecycle tests.

| Area | In place (CP2) | Still future |
|------|----------------|--------------|
| Lifecycle contracts | `CapabilityLifecycleState`, `CapabilityRecord`, manifest/payload mapping helpers | Full registry replacement |
| Control plane | `CapabilityLifecycleManager` → `capability.lifecycle.snapshot` → AppState `capability_lifecycle` | Execution Envelope |
| Settings → tracing | `otel_enabled`, `otel_endpoint` in schema/snapshot; read once at startup in `service_factory` | Hot-reload on `settings.updated` |
| Observability | OTLP HTTP exporter when endpoint set and OTel enabled | Dynamic exporter switching |
| Receipts / routing | Existing orchestration receipt + routing topics consumed by lifecycle manager | Unified Receipts, Router v2 |
| Integrations | Runtime + orchestration health paths | Calendar/email adapters |

### Settings → tracing propagation

Tracing is configured **once at service startup** from `SettingsService.get_snapshot()`:

- `otel_enabled=False` → `TracingService` is a no-op (Invariant 9 telemetry firewall respected).
- `otel_enabled=True` + `otel_endpoint` → OTLP HTTP exporter (`/v1/traces` appended when missing).
- No hot-reload: changing OTel settings requires service restart (documented limitation for CP2).

## Week 1 — Provider SDK

- Package: `ai_command_center/provider_sdk/`
- Adapters for orchestration and runtime providers
- Certification CLI: `python -m ai_command_center.provider_sdk.cli provider test <id> [--certify]`
- Lifecycle mapping: `provider_sdk/capability_lifecycle_mapping.py`

## Week 2 — Observability

- `TracingService` maps bus topics to OpenTelemetry spans
- Topics: intent classification, routing, provider selection, receipt, truth, response
- Optional OTel deps in `requirements.txt` (no-op when unavailable)
- Settings: `otel_enabled`, `otel_endpoint` (see CP2 propagation above)

## Week 3 — Diagnostics

- **Runtime Inspector 2.0** (`ui/runtime_inspector.py`) — Ctrl+Shift+R
- `provider_health_map` in AppState from `orchestration.provider.health` + `capability.providers.ready`
- `capability_lifecycle` in AppState from `capability.lifecycle.snapshot`
- `execution_runs` table + `ExecutionRunService` + `ReplayRunner`

## Week 4 — Manifests & Certification

- Extended `RuntimeProviderManifest` and `OrchestrationProviderManifest`
- Validator in `provider_sdk/registry.py` with dev-mode certification warnings (`ACC_DEV_MODE=1`)
- **Capability Explorer** tab in Runtime Inspector
- Six certification badges in `provider_sdk/testing.py`:
  - Receipt Safe, Truth Safe, Observable, Replay Safe, Deterministic, Permission Safe

## Bus topics (orchestration tracing)

| Topic | Span |
|-------|------|
| `orchestration.intent.classified` | IntentClassification |
| `orchestration.routing.completed` | Routing |
| `orchestration.provider.selected` | ProviderSelection |
| `orchestration.receipt` | ExecutionReceipt |
| `orchestration.truth.validated` | TruthBoundary |
| `orchestration.run.snapshot` | Response |

## Bus topics (capability lifecycle)

| Topic | Producer | Consumer |
|-------|----------|----------|
| `capability.providers.ready` | Runtime provider registry | Lifecycle manager, AppState |
| `orchestration.provider.health` | Orchestration service | Lifecycle manager, AppState |
| `capability.lifecycle.snapshot` | CapabilityLifecycleManager | AppState |

## Example manifests

- Runtime: `plugins/runtime_manifests/*.yaml`
- Orchestration: `plugins/orchestration_manifests/system_facts.yaml`

## MCP

MCP integration is external. The Capability Explorer links to the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) — not embedded in ACC.
