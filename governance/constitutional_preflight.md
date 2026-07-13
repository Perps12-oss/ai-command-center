# CONSTITUTIONAL PRE-FLIGHT

Task Description:
ACC Blueprint Resolutions — Phase 3: CapabilityLibrarySnapshot AppState projection.
Adds an immutable AppState.capability_library: CapabilityLibrarySnapshot field
consolidating the existing capability_lifecycle (CapabilityRecord tuples) and
capability_prompt_catalog (raw dict tuples) into a single typed snapshot.
Reducer consumes CAPABILITY_PROVIDERS_READY, CAPABILITY_LIFECYCLE_SNAPSHOT,
CAPABILITY_CATALOG_RESULT. All three topics already in APP_STATE_TOPICS.
Existing capability_lifecycle + capability_prompt_catalog fields preserved for
backward compatibility. No new topics, services, or DB changes.

Files Reviewed:
- PROJECT_CONSTITUTION_V4.md
- AGENTS.md
- docs/ARCHITECTURE.md
- docs/architecture/VNEXT_STATE_DRIVEN_BLUEPRINT.md
- ai_command_center/core/app_state.py
- ai_command_center/core/events/topics.py
- ai_command_center/domain/capability_lifecycle.py
- governance/constitutional_preflight.md

Authorities Reviewed:
- Level 1: PROJECT_CONSTITUTION_V4.md
- Level 2: AGENTS.md, docs/ARCHITECTURE_ENFORCEMENT.md
- Level 3: docs/ARCHITECTURE.md, ai_command_center/core/contracts.py, ai_command_center/core/events/topics.py

Protected Assets Impacted:
- AppState Projection System (Tier A) — 1 new field added; populated by pure reducer only
- Existing fields capability_lifecycle + capability_prompt_catalog — preserved unchanged

Sources of Truth Impacted:
- AppState source of truth: ai_command_center/core/app_state.py (new field and reducer)
- New domain module: ai_command_center/domain/capability_library_snapshot.py

Architectural Invariants Impacted:
- Invariant 1: Ownership Flow preserved
- Invariant 2: UI Isolation — no UI changes
- Invariant 4: AppState Governance — new field populated by reducer only
- Invariant 8: Topic Governance — only already-registered topics consumed

Contracts Impacted:
- None — all three consumed topics already registered; no new contracts required

Gate Impact Assessment:
- No APP_STATE_TOPICS changes (topics already present)
- No new topics, no contract versions, no schema changes
- No existing reducer signatures changed
- No gate removals or bypasses permitted

Historical Gates Impacted:
- verify_constitution.py
- scripts/arch_lint.py --baseline tests/arch_lint_baseline.json
- python3 -m pytest (full suite)
- python3 -m ruff check ai_command_center

Regression Risk:
Low. Additive only: new domain module, new AppState field defaulting to empty snapshot,
new reducer returning state unchanged for non-matching topics. Existing
capability_lifecycle and capability_prompt_catalog fields untouched.

Constitutional Status:

APPROVED
