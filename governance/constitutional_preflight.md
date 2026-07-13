# CONSTITUTIONAL PRE-FLIGHT

Task Description:
ACC Blueprint Resolutions — Phase 9: ServiceRegistrySnapshot AppState projection.
Adds an immutable AppState.service_registry: ServiceRegistrySnapshot field that
consolidates the flat services tuple with per-service lifecycle history and a
health trend. Wires the four canonical service lifecycle topics that BaseService
publishes (SERVICE_STARTED, SERVICE_READY, SERVICE_STOPPED, SERVICE_ERROR) but
that AppStateStore was silently dropping because only SERVICE_STATE_CHANGED was
in APP_STATE_TOPICS. The existing services tuple is preserved for backward
compatibility. No new topics, services, or DB changes.

Files Reviewed:
- PROJECT_CONSTITUTION_V4.md
- AGENTS.md
- docs/ARCHITECTURE.md
- docs/ARCHITECTURE_ENFORCEMENT.md
- docs/architecture/VNEXT_STATE_DRIVEN_BLUEPRINT.md
- ai_command_center/services/base.py
- ai_command_center/core/contracts.py
- ai_command_center/core/events/topics.py
- ai_command_center/core/app_state.py (AppState, APP_STATE_TOPICS, _reduce_service_state, _DEFAULT_REDUCERS)
- ai_command_center/domain/service_state.py
- ai_command_center/domain/permission_check_snapshot.py (pattern reference)
- governance/constitutional_preflight.md

Authorities Reviewed:
- Level 1: PROJECT_CONSTITUTION_V4.md
- Level 2: AGENTS.md, docs/ARCHITECTURE_ENFORCEMENT.md
- Level 3: docs/ARCHITECTURE.md, ai_command_center/core/contracts.py, ai_command_center/core/events/topics.py

Protected Assets Impacted:
- AppState Projection System (Tier A) — 1 new field added; populated by pure reducer only
- EventBus Topic Registry (Tier A) — four canonical service topics already registered; only AppState subscription wiring changes
- Service Lifecycle Framework (Tier B) — consumer side only; no BaseService changes

Sources of Truth Impacted:
- AppState source of truth: ai_command_center/core/app_state.py (new field, topic wiring, reducer)
- New domain module: ai_command_center/domain/service_registry_snapshot.py
- Service operational state remains authoritative in BaseService._state

Architectural Invariants Impacted:
- Invariant 1: Ownership Flow preserved
- Invariant 2: UI Isolation — no UI changes
- Invariant 4: AppState Governance — new field populated by reducer only
- Invariant 8: Topic Governance — only canonical, already-registered topics consumed

Contracts Impacted:
- APP_STATE_TOPICS subscription list in ai_command_center/core/app_state.py (adds four existing topics)
- New ServiceRegistrySnapshot dataclass contract in ai_command_center/domain/

Gate Impact Assessment:
- Adds SERVICE_STARTED, SERVICE_READY, SERVICE_STOPPED, SERVICE_ERROR to APP_STATE_TOPICS
  (all four already registered in topics.py)
- No new topic definitions, no contract versions, no schema changes
- Existing services tuple preserved unchanged
- No gate removals or bypasses permitted

Historical Gates Impacted:
- verify_constitution.py
- scripts/arch_lint.py --baseline tests/arch_lint_baseline.json
- python3 -m pytest (full suite)
- python3 -m ruff check ai_command_center

Regression Risk:
Low. Additive wiring and new snapshot. The four lifecycle topics were previously
published but not consumed by AppStateStore; wiring them cannot break existing
consumers. Existing services field behavior is preserved.

Constitutional Status:

APPROVED
