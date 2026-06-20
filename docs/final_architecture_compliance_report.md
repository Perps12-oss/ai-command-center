# Final Architecture Compliance Report

## Scope

This report summarizes the architecture cleanup pass against the boundaries defined in `AGENTS.md` and `docs/ARCHITECTURE_ENFORCEMENT.md`.

The earlier baseline comes from `docs/architecture_integrity_report.md`. The after-state reflects the current repo state after the topic-literal and event-bus cleanup pass in this session.

## Before / After

| Violation type | Before | After |
| --- | ---: | ---: |
| Direct file access outside repositories | 10 | 8 |
| SQLite access outside repositories | 1 | 1 |
| UI component calling services directly | 0 | 0 |
| Service calling another service directly | 5 | 0 |
| EventBus topic string literal not defined in `topics.py` | 6 | 0 |
| Settings access bypassing `SettingsService` | 1 | 1 |
| Domain object represented as raw dict | 1 | 1 |

## What Changed

The following architecture violations were removed in this pass:

- UI layer event wiring now uses canonical topic constants instead of hard-coded strings.
- Telemetry capture and derived metrics now rely on `core/events/topics.py` for topic names.
- The chat coordination path no longer performs direct service-to-service calls.
- Settings request handling now subscribes through the canonical settings request topic.
- The activity feed and background controller now subscribe through the topic registry.
- Stub Ollama event emission now uses the topic registry.

## Residual Debt

The repository still has open work in these areas:

- Persistence ownership is not fully complete; some services still access files directly.
- `ObsidianService` still bypasses the canonical settings service boundary.
- `db/conversation_repository.py` still uses a raw dict contract in one path.

## Result

The cleanup pass materially improved boundary enforcement and removed the repo-wide topic-literal violation class. The remaining open items are persistence and contract-shape issues, not bus wiring drift.