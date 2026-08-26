# Constitutional Pre-Flight — DB lock + segfault runtime failure

**Date:** 2026-08-26  
**Task:** Investigate reproducible `sqlite3.OperationalError: database is locked` followed by process segfault (`exit 139`) during runtime/startup-shutdown paths; implement smallest coherent fix without architecture redesign.

## Authorities reviewed

- `PROJECT_CONSTITUTION_V4.md` (Article II, III, VII, VIII, X, XVII)
- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/governance/IMPLEMENTATION_GUIDE.md`
- `ai_command_center/core/contracts.py`
- `ai_command_center/core/events/topics.py`

## Files reviewed before implementation

- `ai_command_center/application.py`
- `ai_command_center/core/service_manager.py`
- `ai_command_center/core/event_bus.py`
- `ai_command_center/db/connection.py`
- `ai_command_center/db/conn_sync.py`
- `ai_command_center/db/repository.py`
- `ai_command_center/services/settings_service.py`
- `ai_command_center/core/settings/settings_service.py`
- `ai_command_center/repositories/goal_repository.py`
- `ai_command_center/core/service_factory.py`

## Protected assets impacted

- Tier A: EventBus architecture, repository ownership model
- Tier B: Settings system, service lifecycle framework

Impact is **behavior-preserving bugfix** only (ordering/locking safety), no ownership boundary changes.

## Sources of truth impacted

- SQLite runtime connection behavior (`ai_command_center/db/*`)
- Application lifecycle sequencing (`ApplicationCore.startup/shutdown`)

No new source of truth introduced.

## Architectural invariants impacted

- Invariant 1 (UI → AppState → EventBus → Services → Repositories → Storage): preserved
- Invariant 3 (EventBus governance): preserved
- Invariant 5 (Repository ownership): preserved
- Invariant 10/11 (verification + SoT integrity): preserved

## Contracts impacted

- No topic schema changes planned.
- No service API shape changes planned.
- Existing event flow and repository contracts must remain intact.

## Gate impact assessment

- Expected gate type: refactor-level runtime safety fix.
- Must not regress service lifecycle or EventBus shutdown behavior.
- Must add runtime evidence and targeted regression test(s) where feasible.

## Historical gate impact

- No gate removal, bypass, or supersession planned.
- Existing gate guarantees remain in force.

## Regression risk

- Medium risk area: shutdown ordering and concurrent DB access.
- Mitigation: targeted instrumentation, focused repro scripts, narrow code changes, targeted tests.

## Constitutional status

**APPROVED** — proceed with minimal runtime-safe implementation after evidence collection.
