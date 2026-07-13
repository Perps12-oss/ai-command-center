# CONSTITUTIONAL PRE-FLIGHT

Task Description:
ACC Blueprint Resolutions — Phase 5: AgentPipelineSnapshot AppState projection.
Adds an immutable AppState.agent_pipeline: AgentPipelineSnapshot field consolidating
the existing agent_runs (tuple[AgentRunItem]), active_agent_run_id, active_agent_run_ids,
active_agent_pipeline_id, agent_pipeline_stage, agent_pipeline_planned_tools into a
single typed snapshot. Reducer consumes AGENT_SPAWNED, AGENT_TASK_REQUEST,
AGENT_TASK_COMPLETE, AGENT_TERMINATED, AGENT_PIPELINE_STARTED, AGENT_PIPELINE_STAGE,
AGENT_PIPELINE_PLANNED, AGENT_PIPELINE_COMPLETE. All topics already in APP_STATE_TOPICS.
Existing fields preserved for backward compatibility. No new topics, services, or DB changes.

Files Reviewed:
- PROJECT_CONSTITUTION_V4.md
- AGENTS.md
- docs/ARCHITECTURE.md
- docs/architecture/VNEXT_STATE_DRIVEN_BLUEPRINT.md
- ai_command_center/core/app_state.py (lines 412-423, 505-512, 1237-1384)
- ai_command_center/core/events/topics.py
- governance/constitutional_preflight.md

Authorities Reviewed:
- Level 1: PROJECT_CONSTITUTION_V4.md
- Level 2: AGENTS.md, docs/ARCHITECTURE_ENFORCEMENT.md
- Level 3: docs/ARCHITECTURE.md, ai_command_center/core/contracts.py, ai_command_center/core/events/topics.py

Protected Assets Impacted:
- AppState Projection System (Tier A) — 1 new field added; populated by pure reducer only
- Existing agent_runs, active_agent_run_id/ids, pipeline fields — preserved unchanged

Sources of Truth Impacted:
- AppState source of truth: ai_command_center/core/app_state.py (new field and reducer)
- New domain module: ai_command_center/domain/agent_pipeline_snapshot.py

Architectural Invariants Impacted:
- Invariant 1: Ownership Flow preserved
- Invariant 2: UI Isolation — no UI changes
- Invariant 4: AppState Governance — new field populated by reducer only
- Invariant 8: Topic Governance — only already-registered topics consumed

Contracts Impacted:
- None — all eight consumed topics already registered; no new contracts required

Gate Impact Assessment:
- No APP_STATE_TOPICS changes (all topics already present)
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
new reducer returning state unchanged for non-matching topics. Existing agent_runs,
active_agent_run_id, active_agent_run_ids, pipeline fields unchanged.

Constitutional Status:

APPROVED
