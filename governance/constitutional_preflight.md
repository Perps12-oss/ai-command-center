# CONSTITUTIONAL PRE-FLIGHT

Task Description:
ACC Blueprint Resolutions — Phase 2: WorldModelSnapshot AppState projection.
Per Resolution 3, adds an immutable AppState.world_model: WorldModelSnapshot field
populated by a pure reducer consuming WORLD_MODEL_MUTATION_APPLIED,
WORLD_MODEL_GRAPH_REFRESHED, WORLD_MODEL_NODE_SELECTED, WORLD_MODEL_NODE_DESELECTED,
ENTITY_CREATED, ENTITY_UPDATED, ENTITY_DELETED, RUNTIME_WORLD_MODEL_APPLY_COMPLETED,
and GOAL_* topics. The existing WorldModelState mutable object is preserved unchanged
for current UI consumers. No new topics, services, or DB changes.

Files Reviewed:
- PROJECT_CONSTITUTION_V4.md
- AGENTS.md
- docs/ARCHITECTURE.md
- docs/architecture/VNEXT_STATE_DRIVEN_BLUEPRINT.md
- ai_command_center/core/app_state.py
- ai_command_center/core/events/topics.py
- ai_command_center/core/state/world_model_state.py
- ai_command_center/ui/views/world_explorer_view.py
- ai_command_center/ui/shell/view_manager.py
- governance/constitutional_preflight.md

Authorities Reviewed:
- Level 1: PROJECT_CONSTITUTION_V4.md
- Level 2: AGENTS.md, docs/ARCHITECTURE_ENFORCEMENT.md
- Level 3: docs/ARCHITECTURE.md, ai_command_center/core/contracts.py, ai_command_center/core/events/topics.py

Protected Assets Impacted:
- AppState Projection System (Tier A) — 1 new field added; populated only by pure reducer
- Topic Registry (Tier A) — APP_STATE_TOPICS extended with 9 world model topics
- WorldModelState mutable object (Tier B) — preserved unchanged, no edits

Sources of Truth Impacted:
- AppState source of truth: ai_command_center/core/app_state.py (new field and reducer)
- New domain module: ai_command_center/domain/world_model_snapshot.py

Architectural Invariants Impacted:
- Invariant 1: Ownership Flow preserved (UI → AppState → EventBus direction for future consumers)
- Invariant 2: UI Isolation — no UI changes
- Invariant 3: WorldModel ownership split honoured — Brain WorldModel and Entity Graph remain distinct
- Invariant 4: AppState Governance — new field populated by reducer only, never by UI
- Invariant 8: Topic Governance — only already-registered topics consumed

Contracts Impacted:
- None — all consumed topics are already registered; no new contracts required

Gate Impact Assessment:
- APP_STATE_TOPICS extended — verify_constitution.py must still pass
- No new topics, no new contract versions, no schema changes
- No existing reducer signatures changed
- No gate removals or bypasses permitted

Historical Gates Impacted:
- verify_constitution.py
- scripts/arch_lint.py --baseline tests/arch_lint_baseline.json
- python3 -m pytest (full suite)
- python3 -m ruff check ai_command_center

Regression Risk:
Low. All changes are additive: new domain module with frozen dataclasses,
new AppState field defaulting to empty WorldModelSnapshot, new reducer that
returns state unchanged for all non-matching topics. The existing WorldModelState
mutable object and all its UI consumers are untouched.

Constitutional Status:

APPROVED
