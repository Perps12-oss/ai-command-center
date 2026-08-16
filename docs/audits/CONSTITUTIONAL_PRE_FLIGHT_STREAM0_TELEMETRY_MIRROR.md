# Constitutional Pre-Flight — Stream 0 telemetry Claude-home mirror

**Date:** 2026-08-16  
**Task:** Stream 0 blocker 0.3 — session telemetry export already flushes on `TelemetryService` unload; operators inspect `~/.claude/telemetry/` and `~/.claude/stats-cache.json`, which the product path never wrote. Add a derived local mirror. Blockers 0.1 and 0.2 are already on `main` (no code).  
**Status:** APPROVED

## Task Description

Keep SQLite + `%APPDATA%/AICommandCenter/telemetry` (or `ACC_TELEMETRY_EXPORT_DIR`) as the ACC export location. After a successful session export, also write the same snapshot under `~/.claude/telemetry/` and merge model inventory into `~/.claude/stats-cache.json`. Optionally refresh that export on a time interval while the service is running. Observation only; no new EventBus topics; no service-to-service calls.

## Authorities Reviewed

- `PROJECT_CONSTITUTION_V4.md` (Art. X pre-flight; Inv. 9 telemetry firewall; Inv. 11 SoT; Inv. 13 host supremacy)
- `AGENTS.md` / `docs/ARCHITECTURE_ENFORCEMENT.md`
- `docs/ARCHITECTURE.md`
- `docs/architecture/adr/ADR-011_TELEMETRY_BACKENDS.md` (Proposed / PARKED — not implemented)
- `docs/architecture/proposals/WAVE_1_GATE_2_DECISIONS.md` (Stream 0 is tooling; not stream A–F Gate 4)

## Files Reviewed

- `ai_command_center/telemetry/session_export.py`
- `ai_command_center/services/telemetry_service.py`
- `ai_command_center/application.py`
- `ai_command_center/platform/runtime_paths.py`
- `tests/test_telemetry_export.py`
- `tests/conftest.py`
- `.claude/skills/acc-preflight/SKILL.md`, `acc-audit`, `acc-session` (BOM/frontmatter already valid on `main`)

## Protected Assets Impacted

None. No ExecutionAuthority, receipts, TruthBoundary, or UI changes.

## Sources of Truth Impacted

None. Telemetry SQLite remains SoT for events. The `~/.claude/` files are a derived inspectability copy, not an authority.

## Architectural Invariants Impacted

- **Inv. 9:** Export remains a read-back of persisted rows. Mirror does not change runtime decisions.
- **Inv. 11:** Claude Code paths are not SoT; merge preserves unknown keys in an existing `stats-cache.json`.
- **Inv. 13:** No Claude Code API; local files only. ACC runtime data dir stays the product location.

## Contracts Impacted

`TelemetryEvent` unchanged. `telemetry.event` unchanged. ADR-011 exporters are not introduced.

## Gate Impact Assessment

No historical phase gate. Stream A–F Gate 4 remains blocked. This is Stream 0 tooling/export location only.

## Historical Gate Impact

None.

## Regression Risk

Low. Tests already isolate `ACC_TELEMETRY_EXPORT_DIR`. Suite will disable the Claude mirror by default so pytest cannot write into a real `~/.claude`.

## Constitutional Status

APPROVED
