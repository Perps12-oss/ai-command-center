# ADR-011: Layered Telemetry Backends

**Status:** Proposed  
**Disposition:** PARKED / NOT REQUIRED — **NOT IMPLEMENTATION WORK.** Live telemetry is `TelemetryService` → EventBus. Do not implement OTel/PostHog/Langfuse exporters from this ADR.  
**Date:** 2026-07-27  
**Deciders:** Architecture Review (Tom)  
**Supersedes:** —  
**Related:** `research/patterns/PAT-007.md`, `research/integration/INT-007.md`, `research/decisions/RD-001.md`, `AGENTS.md` telemetry requirements

---

## Context

ACC already publishes `TelemetryEvent` objects to the `EventBus` through `TelemetryService`. A single sink does not fit all deployments: local logs, OpenTelemetry, PostHog, and Langfuse are useful in different contexts. `block/goose` uses `tracing-subscriber` layers to route events to multiple backends.

## Decision

Extend `TelemetryService` with a pluggable exporter model. Each exporter subscribes to `telemetry.event`, transforms the event to its backend format, and writes it asynchronously. Exporters are enabled via `SettingsSnapshot`.

### Contract

- `TelemetryEvent` remains the canonical domain event.
- `telemetry.event` is the only topic producers publish to.
- `TelemetryService` loads enabled exporters from settings.
- Exporters implement `TelemetryExporter.export(event) -> None`.
- Exporter failures are isolated: one backend failure does not drop events to others.
- PII must be scrubbed before any external backend receives an event.

## Rationale

| Factor | Without exporter model | With exporter model |
|--------|------------------------|---------------------|
| Backend variety | One hard-coded sink | Multiple optional backends |
| Local development | Logs to file/console | Same pipeline, different exporters |
| Production | Custom integration per deployment | OTel/PostHog/Langfuse via settings |
| Failure isolation | One backend outage can block telemetry | Async queue per exporter |

## Consequences

### Positive

- No code changes needed to add a new sink.
- Standard `TelemetryEvent` keeps instrumentation idiomatic.
- Failures in one exporter do not drop others.

### Negative / Risk

- External backends add network and dependency risk.
- PII leakage risk requires explicit scrubbing.
- Overlapping log/telemetry streams can create noise.

## Implementation Notes

- Add `ai_command_center/telemetry/exporters/` with `ConsoleExporter`, `FileJsonExporter`, `OpenTelemetryExporter`, `LangfuseExporter`, `PostHogExporter`.
- `TelemetryService` initializes exporters from `SettingsSnapshot` during `STARTING`.
- Each exporter runs in its own async queue/worker.
- Scrubbing rules live in `ai_command_center/telemetry/pii_scrubber.py` and are applied before external export.

## Verification

- Unit test: each exporter receives `TelemetryEvent` and formats correctly.
- Test: one exporter failure does not stop others.
- Test: PII fields are redacted before external export.
- Test: `TelemetryService` lifecycle starts/stops all exporters cleanly.
