# Provider Platform

Four-week delivery cycle for ACC provider SDK, observability, diagnostics, and certification.

## Architecture

```text
UI (Runtime Inspector)
  → AppState
  → EventBus
  → Services (Orchestration, Tracing, ExecutionRun)
  → Repositories
  → SQLite / manifests
```

External runtimes integrate only through manifests and the Agent Runtime Interface (`docs/architecture/AGENT_RUNTIME_INTERFACE.md`). ACC remains system of record.

## Week 1 — Provider SDK

- Package: `ai_command_center/provider_sdk/`
- Adapters for orchestration and runtime providers
- Certification CLI: `python -m ai_command_center.provider_sdk.cli provider test <id> [--certify]`

## Week 2 — Observability

- `TracingService` maps bus topics to OpenTelemetry spans
- Topics: intent classification, routing, provider selection, receipt, truth, response
- Optional OTel deps in `requirements.txt` (no-op when unavailable)

## Week 3 — Diagnostics

- **Runtime Inspector 2.0** (`ui/runtime_inspector.py`) — Ctrl+Shift+R
- `provider_health_map` in AppState from `orchestration.provider.health` + `capability.providers.ready`
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

## Example manifests

- Runtime: `plugins/runtime_manifests/*.yaml`
- Orchestration: `plugins/orchestration_manifests/system_facts.yaml`

## MCP

MCP integration is external. The Capability Explorer links to the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) — not embedded in ACC.
