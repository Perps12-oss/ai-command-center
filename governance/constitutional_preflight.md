# CONSTITUTIONAL PRE-FLIGHT

Task Description:
Hard-stop residual navigate freezes after 2 sidebar clicks. User logs show
dozens of ui.navigate budget hits then ollama.status ~17s — either an old
binary without #106, or remaining re-entry / nested bus publish amplification.
Add navigate reentrancy + same-view short-circuit; remove redundant
ollama.status UI subscription (SYSTEM_SNAPSHOT already carries online);
stop nested EVENT_OBSERVABILITY_METRIC publishes from budget exceedances
(storm amplifier); keep Telemetry off the critical path for navigate.

Files Reviewed:
- PROJECT_CONSTITUTION_V4.md
- AGENTS.md
- docs/architecture/ASYNC_EVENTBUS_POLICY.md
- ai_command_center/ui/shell/view_manager.py
- ai_command_center/ui/shell/event_coordinator.py
- ai_command_center/core/event_bus.py
- ai_command_center/services/telemetry_service.py
- ai_command_center/services/system_monitor_service.py

Authorities Reviewed:
- Level 1: PROJECT_CONSTITUTION_V4.md
- Level 2: AGENTS.md
- Level 3: ASYNC_EVENTBUS_POLICY.md, topics.py

Protected Assets Impacted:
- EventBus observability side-publish only (no topic contract change)
- UI shell navigate apply path
- Telemetry recording path for navigate (optional defer)

Sources of Truth Impacted:
- None. ollama_online remains via SYSTEM_SNAPSHOT → AppState.

Architectural Invariants Impacted:
- Invariant 1 / 2 preserved; strengthens Tk thread affinity

Contracts Impacted:
- Behavioral: _navigate is non-reentrant and no-ops when already on view
- Budget exceedance no longer sync-publishes EVENT_OBSERVABILITY_METRIC

Gate Impact Assessment:
- No gate removals; add navigate reentrancy tests

Constitutional Status:

APPROVED
