# CONSTITUTIONAL PRE-FLIGHT

Task Description:
ACC Blueprint Pre-Implementation Resolutions — Phase 0.
Implements the seven resolutions required before frontend blueprint coding begins:
correlation ID propagation through Execution/ExecutionRun/AgentRun domains,
8 new EventBus topics (FOCUS_SELECTED, OPERATION_LOADED, JOURNAL_ENTRY_APPENDED, etc.),
OperationIndexerService + operation_index SQLite table,
OperationSnapshot and JournalEntry domain objects,
GoalRepository.get_by_correlation() and ExecutionRunRepository.get_by_correlation() methods,
and AppState journal/operation_library_index reducers.

Files Reviewed:
- PROJECT_CONSTITUTION_V4.md
- AGENTS.md
- docs/ARCHITECTURE.md
- docs/architecture/VNEXT_STATE_DRIVEN_BLUEPRINT.md
- docs/architecture/ARCHITECTURE_TRANSITION_PLAN.md
- ai_command_center/core/contracts.py
- ai_command_center/core/events/topics.py
- ai_command_center/core/app_state.py
- ai_command_center/domain/correlation.py
- ai_command_center/domain/goal.py
- ai_command_center/domain/execution.py
- ai_command_center/domain/execution_run.py
- ai_command_center/domain/world_model.py
- ai_command_center/repositories/goal_repository.py
- ai_command_center/repositories/execution_run_repository.py
- ai_command_center/core/service_factory.py
- governance/constitutional_preflight.md

Authorities Reviewed:
- Level 1: PROJECT_CONSTITUTION_V4.md
- Level 2: AGENTS.md, docs/ARCHITECTURE_ENFORCEMENT.md
- Level 3: docs/ARCHITECTURE.md, ai_command_center/core/contracts.py, ai_command_center/core/events/topics.py

Protected Assets Impacted:
- EventBus Architecture (Tier A) — 8 new topics added to canonical registry
- AppState Projection System (Tier A) — new fields added; existing reducers untouched
- Topic Registry (Tier A) — topics.py extended; all new topics in __all__
- Contract Registry (Tier A) — contracts.py extended with operation contract version
- Repository Layer (Tier B) — new table schemas; existing table schemas preserved
- Service Lifecycle Framework (Tier B) — new OperationIndexerService registered

Sources of Truth Impacted:
- Topic source of truth: ai_command_center/core/events/topics.py (extended)
- Contract source of truth: ai_command_center/core/contracts.py (extended)
- Domain model source of truth: ai_command_center/domain/ (Execution, ExecutionRun extended; new files added)
- Persistence source of truth: repositories/ (new operation_index_repository; existing repos extended)
- AppState source of truth: ai_command_center/core/app_state.py (new fields and reducers added)

Architectural Invariants Impacted:
- Invariant 1: Ownership Flow preserved (UI → AppState → EventBus → Services → Repositories → Storage)
- Invariant 2: UI Isolation — no UI changes in Phase 0
- Invariant 3: EventBus Governance — all new topics registered in topics.py before use
- Invariant 4: AppState Governance — all new AppState fields populated by reducers only
- Invariant 5: Repository Ownership — OperationIndexerService reads only from event payloads; repositories own storage
- Invariant 8: Topic Governance — payload shapes documented inline in topics.py
- Invariant 11: Source-of-Truth Integrity — no duplicate domain modules; all changes in domain/

Contracts Impacted:
- ContextBundle v1.2 (read-only dependency, no change)
- command.routed v1.0 (read-only dependency, no change)
- tool.invoke / tool.result v1.0 (no change)
- operation contract v1.0 (NEW — OPERATION_LOAD_REQUEST / OPERATION_LOADED payload shape)

Gate Impact Assessment:
- topics.py __all__ extended — verify_constitution.py must still pass
- contracts.py extended — verify_contracts.py must still pass
- New SQLite tables added via CREATE TABLE IF NOT EXISTS — no migration conflict
- ExecutionRun schema amended (correlation_id column) — additive only, backward compatible
- No existing topic strings changed, no existing reducer signatures changed
- No gate removals or bypasses permitted

Historical Gates Impacted:
- verify_constitution.py
- verify_contracts.py
- scripts/arch_lint.py --baseline tests/arch_lint_baseline.json
- python3 -m pytest (full suite)
- python3 -m ruff check ai_command_center

Regression Risk:
Low. All changes are additive: new domain fields with defaults, new topics, new tables with IF NOT EXISTS,
new AppState tuple fields defaulting to empty. No existing reducer, service, or repository signature is changed.
The only risk surface is the ExecutionRun correlation_id migration — handled via ALTER TABLE IF NOT EXISTS pattern.

Constitutional Status:

APPROVED
