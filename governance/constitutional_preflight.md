# CONSTITUTIONAL PRE-FLIGHT

Task Description:
Fix UI freeze after launch / page navigation caused by a UI_NAVIGATE
feedback loop: ViewManager._navigate publishes UI_NAVIGATE, and
EventCoordinator._on_ui_navigate was calling _navigate again (which
republishes), starving the Tk main loop. Restore the former
COMMAND_ROUTED guard semantics — apply external navigate intents via
_show_view only; ignore UI-sourced echoes. No new topics, services,
or schema changes.

Files Reviewed:
- PROJECT_CONSTITUTION_V4.md
- AGENTS.md
- docs/ARCHITECTURE.md
- docs/ARCHITECTURE_ENFORCEMENT.md
- ai_command_center/core/events/topics.py
- ai_command_center/ui/shell/event_coordinator.py
- ai_command_center/ui/shell/view_manager.py
- ai_command_center/ui/controller.py
- ai_command_center/orchestration/state_capability_tools.py
- governance/constitutional_preflight.md

Authorities Reviewed:
- Level 1: PROJECT_CONSTITUTION_V4.md
- Level 2: AGENTS.md, docs/ARCHITECTURE_ENFORCEMENT.md
- Level 3: docs/ARCHITECTURE.md, ai_command_center/core/events/topics.py

Protected Assets Impacted:
- EventBus Topic Registry (Tier A) — UI_NAVIGATE consumer semantics only; topic unchanged
- AppState Projection System (Tier A) — untouched
- UI shell (renderer) — event coordinator + navigate apply path only

Sources of Truth Impacted:
- None. Navigation intent remains EventBus UI_NAVIGATE; view visibility remains shell-local.

Architectural Invariants Impacted:
- Invariant 1: Ownership Flow preserved (UI → EventBus; external tools publish intent)
- Invariant 2: UI Isolation — UI still does not own storage/services
- Invariant 8: Topic Governance — no new topics; existing UI_NAVIGATE only

Contracts Impacted:
- Behavioral contract of UI_NAVIGATE shell consumer: must not re-enter
  ViewManager._navigate (which republishes). External sources apply via _show_view.

Gate Impact Assessment:
- No gate removals or bypasses
- Adds regression test for navigate non-reentry
- Existing UI / constitution / UCGS gates remain in force

Historical Gates Impacted:
- python3 -m pytest (UI + focused navigate regression)
- python3 -m ruff check ai_command_center
- scripts/verify_constitution.py
- tools/ucgs_runner.py + ucgs_ci_gate.py

Regression Risk:
Low. Restores pre-migration COMMAND_ROUTED filtering intent (ignore UI echo;
apply non-UI navigate). Sidebar/palette path unchanged (_navigate still
publishes once for telemetry). External state_capability_tools navigate
still applied via _show_view.

Constitutional Status:

APPROVED
