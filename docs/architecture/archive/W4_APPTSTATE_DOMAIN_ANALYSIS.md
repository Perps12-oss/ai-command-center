# W4 AppState Domain Split — Analysis & Decision

**Status:** Complete  
**Date:** 2026-07-10  
**Authority:** `PROGRAM4_GATE_STATUS.md`

---

## Executive Summary

The W4 AppState domain split has been **evaluated and is deemed complete** at the current granularity. Further splits are not recommended unless specific performance or architectural needs emerge.

---

## Current State Module Inventory

| Module | Purpose | Topics Handled |
|--------|---------|----------------|
| `chat_state.py` | Chat stream, history, context | CHAT_*, COMMAND_ROUTED, CONTEXT_SNAPSHOT_CREATED, UI_OPEN_CHAT |
| `workspace_state.py` | Entity graph, workspace selection | ENTITY_*, WORKSPACE_*, UI_SELECT_ENTITY, NOTES_INDEXED |
| `model_state.py` | Model selection snapshot | MODEL_SELECTED |
| `tool_state.py` | Tool execution feed | TOOL_STARTED, TOOL_COMPLETED, TOOL_FAILED |
| `artifact_state.py` | Artifact catalog | ARTIFACT_CREATED, ARTIFACT_UPDATED, ARTIFACTS_LOADED |
| `execution_event_state.py` | Execution event items | EXECUTION_EVENT_APPENDED, EXECUTION_EVENTS_LOADED |
| `execution_timeline_state.py` | Execution timeline stream | EXECUTION_EVENT_APPENDED, EXECUTION_EVENTS_LOADED |
| `execution_state.py` | Execution context/spans | EXECUTION_RUN_*, EXECUTION_STEP_* |
| `inspector_state.py` | Inspector UI state | UI_INSPECT_* |
| `workflow_graph_state.py` | Workflow graph projection | UI_WORKFLOW_*, WORKFLOW_* |
| `automation_workspace_state.py` | Automation workspace | UI_AUTOMATION_*, WORKFLOW_RUNS_LOADED |

---

## Evaluation Criteria

### 1. Coupling Analysis

**Existing splits** are loosely coupled:
- Each module handles a distinct domain (chat, workspace, model, tools)
- Topics are cleanly partitioned across modules
- No cross-module reducer dependencies

**Potential splits considered:**

| Potential Split | Fields | Coupling Analysis |
|----------------|--------|-------------------|
| `telemetry_state` | `recent_artifacts`, `recent_execution_events` | Already split: `artifact_state`, `execution_event_state` handle these |
| `orchestration_state` | `orchestration_run`, `provider_health_map`, `permission_check_*` | Tightly coupled with execution state; would increase complexity |

**Decision:** No new splits needed.

### 2. Performance Analysis

The AppStateStore notifies listeners on any state change. The question is whether further splits would reduce notification frequency.

**Current behavior:**
- Listeners receive full AppState snapshot
- UI components read only their relevant fields
- Snapshot immutability ensures safe reads

**Potential improvement paths:**
1. **Topic-scoped subscriptions** — Already implemented via event topic filtering
2. **Selective state updates** — Would require refactoring AppStateStore architecture
3. **Sub-state stores** — Would increase complexity without clear benefit

**Decision:** Current architecture is sufficient for performance needs.

### 3. Maintainability Analysis

**Benefits of current split:**
- Clear domain boundaries
- Easy to locate reducer logic by domain
- Parallel development on different domains possible

**Risks of further splitting:**
- Increased file count
- More complex import dependencies
- Potential for circular dependencies between tightly-coupled state

**Decision:** Balance achieved.

---

## Recommendation

### ✅ W4 AppState Domain Split: COMPLETE

The current four-way split (`chat_state.py`, `workspace_state.py`, `model_state.py`, `tool_state.py`) plus additional domain-specific modules (`artifact_state.py`, `execution_*_state.py`, etc.) provides:

1. **Clean separation** of concerns
2. **Maintainable file sizes** (each module < 300 lines)
3. **Clear ownership** by domain
4. **Adequate granularity** for current use cases

### Future Consideration: Topic-Scoped Listeners

If performance becomes a concern in the future, consider implementing topic-scoped listeners:

```python
# Potential future enhancement
bus.subscribe_to_topics(
    topics=["TOOL_*", "MODEL_SELECTED"],
    handler=self._on_tool_or_model_change,
)
```

This would reduce notifications without requiring structural changes.

---

## Evidence

| Criterion | Evidence | Status |
|-----------|----------|--------|
| Chat state isolated | `chat_state.py` with 10 reducers | ✅ |
| Workspace state isolated | `workspace_state.py` with 4 reducers | ✅ |
| Model state isolated | `model_state.py` with 1 reducer | ✅ |
| Tool state isolated | `tool_state.py` with 3 reducers | ✅ |
| Execution state isolated | `execution_state.py` + `execution_*_state.py` | ✅ |
| No cross-module dependencies | Each reducer is self-contained | ✅ |
| File sizes manageable | All modules < 300 lines | ✅ |

---

## Conclusion

The W4 AppState domain split is **evaluated and complete**. No further splitting is recommended at this time.

**Next review:** If any of the following occur:
- Specific performance issues traced to AppState notifications
- New domain emerges that doesn't fit existing modules
- File size in any module exceeds 500 lines

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-10 | Initial analysis — W4 split deemed complete |
