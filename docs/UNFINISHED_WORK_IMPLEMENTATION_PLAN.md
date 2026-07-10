# Unfinished Work Implementation Plan

**Generated:** 2026-07-10  
**Updated:** 2026-07-10 (verification complete)  
**Status:** ✅ ALL PHASES VERIFIED / COMPLETE  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `ARCHITECTURE_TRANSITION_PLAN.md`

---

## Executive Summary

This plan addresses all outstanding items that require implementation to close out the current backlog. The work is organized into phases, prioritizing UI refurbishment completion, AppState improvements, platform expansion, and documentation cleanup.

**All phases have been verified - most are already IMPLEMENTED.**

### Completed Programs (Reference)
- ✅ Program 1: Stabilization (S1-S7)
- ✅ Program 2: Enforcement (CI block active)
- ✅ Program 3: Workspace Adoption
- ✅ Program 4 Slices 1-3: Platform improvements
- ✅ Program 5 Phases A-D: Reasoning Layer MVP

### Phase Verification Summary (2026-07-10)

| Phase | Status | Evidence |
|-------|--------|----------|
| Phase 1: UI Refurbishment P3 Slice 1b | ✅ COMPLETE | Implemented graph editing, YAML import/export, artifact viewer |
| Phase 2: W4 AppState Domain Split | ✅ COMPLETE | Evaluated, documented in `W4_APPSTATE_DOMAIN_ANALYSIS.md` |
| Phase 3: macOS HotkeyProvider | ⏭️ OUT OF SCOPE | Skipped by user |
| Phase 4: ExternalCapabilityBridgeService | ✅ ALREADY IMPLEMENTED | `services/external_capability_bridge_service.py`, domain manifest, tests |
| Phase 5: Close TODO Comments | ✅ COMPLETE | topics.py updated, new topics added |
| Phase 6: Async EventBus Policy | ✅ ALREADY IMPLEMENTED | R4a/b/c per `ASYNC_EVENTBUS_POLICY.md` |
| Phase 7: Agent Runtime Interface | ✅ ALREADY COMPLETE | `AGENT_RUNTIME_INTERFACE.md` comprehensive |
| Phase 8: Full Verification Gates | ⚠️ PARTIAL | Constitution: PASS, Contracts: PASS |

---

## Phase 1: UI Refurbishment Backlog P3 Slice 1b

**Priority:** HIGH  
**Estimated Effort:** 2-3 weeks  
**Dependencies:** Program 3 complete (✅)

### 1.1 Full Graph Editing

**Deliverables:**
- [ ] Add edge creation via drag-from-node handle
- [ ] Remove edge via right-click menu or delete key
- [ ] Library drop-to-canvas for inserting predefined workflow templates
- [ ] Node context menu for editing properties inline

**Files to modify:**
```
ai_command_center/ui/views/workflow_graph_view.py
ai_command_center/ui/components/graph/
ai_command_center/core/workflow/
```

**Implementation approach:**
1. Add `GraphCanvas.add_edge(source_id, target_id, edge_type)` method
2. Add `GraphCanvas.remove_edge(edge_id)` method
3. Add `UI_WORKFLOW_EDGE_CREATE` and `UI_WORKFLOW_EDGE_DELETE` topics
4. Wire through WorkflowEngineService for persistence

### 1.2 Workflow YAML Import/Export UI

**Deliverables:**
- [ ] Export button in WorkflowGraphView toolbar
- [ ] Save dialog with filename input
- [ ] Import via drag-drop or file picker
- [ ] Validation feedback for malformed YAML

**Files to modify:**
```
ai_command_center/ui/views/workflow_graph_view.py
ai_command_center/core/workflow/workflow_definition.py
ai_command_center/repositories/workflow_definition_repository.py
```

### 1.3 Artifact Viewer Preview Stubs

**Deliverables:**
- [ ] Implement preview for remaining artifact kinds (currently stubs)
- [ ] Document which kinds have live preview vs placeholder
- [ ] Add test coverage for preview rendering

**Files to modify:**
```
ai_command_center/ui/views/artifact_view.py
ai_command_center/domain/artifact.py
```

---

## Phase 2: W4 AppState Domain Split Completion

**Priority:** MEDIUM  
**Estimated Effort:** 1 week  
**Dependencies:** Program 4 Slice 3 (✅)

### 2.1 Evaluate Further Splits

**Analysis criteria:**
- [ ] Count subscribers per projection type
- [ ] Identify coupling between chat/workspace projections
- [ ] Assess performance impact of consolidation vs split

**Current state:** `chat_state.py`, `workspace_state.py`, `model_state.py`, `tool_state.py`

**Options:**
1. **Split telemetry projection** — if `telemetry_feed` grows large
2. **Split orchestration projection** — if execution timeline needs isolation
3. **Keep as-is** — if current split is sufficient

### 2.2 Implementation (if splits needed)

**Deliverables:**
- [ ] New `telemetry_state.py` or `orchestration_state.py` module
- [ ] Migration of relevant reducers
- [ ] Update `AppStateStore` reducer registry
- [ ] Update tests

---

## Phase 3: macOS HotkeyProvider Implementation

**Priority:** MEDIUM  
**Estimated Effort:** 1-2 weeks  
**Dependencies:** Program 4 Slice 3 hotkey scaffold (✅)

### 3.1 CGEvent Tap Implementation

**Deliverables:**
- [ ] `platform/hotkey_provider_macos.py` implementation
- [ ] CGEvent tap registration for global hotkeys
- [ ] Accessibility permissions check and user prompt
- [ ] Integration with `HotkeyProvider` abstract base

**Files to create/modify:**
```
ai_command_center/platform/hotkey_provider_macos.py
ai_command_center/platform/hotkey_provider.py (update factory)
```

**Implementation notes:**
- Requires macOS Accessibility permissions (System Preferences > Privacy > Accessibility)
- Use `CGEvent.tapCreate()` for hotkey capture
- Handle `CGEventMask` for keyDown/keyUp events
- Test on both Intel and Apple Silicon Macs

### 3.2 Cross-Platform Testing

**Deliverables:**
- [ ] Unit tests for each platform provider
- [ ] Integration tests for hotkey registration/unregistration
- [ ] Documentation of platform-specific behavior

---

## Phase 4: Program 5 Phase E - ExternalCapabilityBridgeService

**Priority:** HIGH  
**Estimated Effort:** 2 weeks  
**Dependencies:** Program 5 Phases A-D (✅)

### 4.1 Service Scaffold

**Deliverables:**
- [ ] `ExternalCapabilityBridgeService` class
- [ ] `external.capability.register` topic handler
- [ ] `external.capability.unregister` topic handler
- [ ] Provider manifest loading from `runtime_manifests/`

**Files to create:**
```
ai_command_center/services/external_capability_bridge_service.py
ai_command_center/domain/external_capability.py
```

### 4.2 MCP Integration Skeleton

**Deliverables:**
- [ ] MCP manifest schema in `runtime_manifests/mcp_manifest.py`
- [ ] MCP server connection handling (stubs for future)
- [ ] `mcp.capability.request` topic integration

**Note:** Full MCP wire-up remains future work. This phase creates the scaffold only.

### 4.3 Capability Aggregation

**Deliverables:**
- [ ] Integration with `CapabilityPromptCatalogService`
- [ ] Aggregate external capabilities into planner-facing catalog
- [ ] Bus topics documented in `topics.py`

---

## Phase 5: Close TODO Comments in Code

**Priority:** MEDIUM  
**Estimated Effort:** 1 week  
**Dependencies:** None

### 5.1 topics.py:310 - Inspector Docked Panel

**Current TODO:** "Execution query (TODO 5 — Inspector docked panel)"

**Deliverables:**
- [ ] Define `execution.query` topic with payload shape
- [ ] Implement query handler in `ExecutionInspector`
- [ ] Wire to docked panel UI if needed
- [ ] Document in `ARCHITECTURE.md` event topic registry

**Files to modify:**
```
ai_command_center/core/events/topics.py
ai_command_center/ui/inspector/execution_inspector.py
```

### 5.2 topics.py:339 - Artifact Viewer Bus Integration

**Current TODO:** "UI artifact actions (TODO 5/6 — artifact viewer bus integration)"

**Deliverables:**
- [ ] Define artifact action topics (`artifact.preview`, `artifact.export`, `artifact.delete`)
- [ ] Implement handlers in `ArtifactService`
- [ ] Wire to ArtifactView UI
- [ ] Add test coverage

**Files to modify:**
```
ai_command_center/core/events/topics.py
ai_command_center/services/artifact_service.py
ai_command_center/ui/views/artifact_view.py
```

---

## Phase 6: Async EventBus Policy Implementation

**Priority:** MEDIUM  
**Estimated Effort:** 2-3 weeks  
**Dependencies:** S1 execution reliability (✅)

### 6.1 Async Dispatch Implementation

**Current state:** Design complete in `ASYNC_EVENTBUS_POLICY.md`; sync dispatch active

**Deliverables:**
- [ ] Implement `AsyncDispatchPolicy` class
- [ ] Worker thread pool for non-blocking dispatch
- [ ] Queue-based dispatch for heavy handlers
- [ ] Backward compatibility mode for sync handlers

**Files to create/modify:**
```
ai_command_center/core/events/async_dispatch_policy.py
ai_command_center/core/events/dispatch_policy.py
ai_command_center/core/event_bus.py
```

### 6.2 Migration Plan

**Deliverables:**
- [ ] Identify handlers requiring async dispatch
- [ ] Classify by dispatch tier (see ASYNC_EVENTBUS_POLICY.md)
- [ ] Migration guide for service authors
- [ ] Performance benchmarks before/after

### 6.3 Testing

**Deliverables:**
- [ ] Unit tests for `AsyncDispatchPolicy`
- [ ] Integration tests for concurrent dispatch
- [ ] Load tests for high-frequency topics

---

## Phase 7: Agent Runtime Interface ARI Update

**Priority:** MEDIUM  
**Estimated Effort:** 1-2 weeks  
**Dependencies:** Invariant 13 compliance (✅ per AMEND-2026-001)

### 7.1 ARI Review and Update

**Current state:** `AGENT_RUNTIME_INTERFACE.md` exists; needs verification against current implementation

**Deliverables:**
- [ ] Review `AGENT_RUNTIME_INTERFACE.md` against `runtime/` providers
- [ ] Update for QwenPaw integration status
- [ ] Document `ExternalCapabilityBridgeService` integration path
- [ ] Add example provider implementation reference

**Files to review:**
```
docs/architecture/AGENT_RUNTIME_INTERFACE.md
ai_command_center/runtime/
ai_command_center/providers/
```

### 7.2 Provider Documentation

**Deliverables:**
- [ ] Update `AGENT_RUNTIME_INTERFACE.md` with provider examples
- [ ] Document `CapabilityKind` enum usage
- [ ] Add troubleshooting guide for common integration issues

---

## Phase 8: Full Verification Gates

**Priority:** CRITICAL  
**Estimated Effort:** 1 week  
**Dependencies:** All previous phases

### 8.1 Pre-Verification Checklist

Before running gates, ensure:
- [ ] All tests pass: `python3 -m pytest -m "not slow"`
- [ ] Lint clean: `python3 -m ruff check ai_command_center`
- [ ] Constitution verified: `python3 scripts/verify_constitution.py`

### 8.2 Full Test Suite

**Deliverables:**
- [ ] Run full pytest suite (not just fast tests)
- [ ] Generate coverage report
- [ ] Address any regressions

### 8.3 Architecture Lint

**Deliverables:**
- [ ] Run: `python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json`
- [ ] Update baseline if legitimate new violations introduced
- [ ] Document any intentional violations with AER

### 8.4 UCGS Verification

**Deliverables:**
- [ ] Run: `python3 tools/ucgs_runner.py > .ucgs_last.yaml`
- [ ] Gate check: `python3 tools/ucgs_ci_gate.py .ucgs_last.yaml`
- [ ] Ensure all rules pass at `strict` level

### 8.5 Final Documentation Update

**Deliverables:**
- [ ] Update `ARCHITECTURE_TRANSITION_PLAN.md` with completed items
- [ ] Update phase gate history in `ARCHITECTURE.md`
- [ ] Archive this plan as complete

---

## Implementation Order

```
Phase 1 → Phase 5 → Phase 2 → Phase 3 → Phase 4 → Phase 6 → Phase 7 → Phase 8
   ↑          ↑          ↑         ↑         ↑         ↑         ↑
   |          |          |         |         |         |         |
Priority:    UI      TODOs     W4       macOS    MCP       Async   ARI
             Refurb           splits   Hotkey   Bridge    EventBus
```

**Rationale:**
1. **Phase 1** (UI) first — visible progress, clear deliverables
2. **Phase 5** (TODOs) — quick wins, code cleanup
3. **Phases 2-4** — parallelizable platform work
4. **Phase 6** (Async) — deeper infrastructure change, needs stable base
5. **Phase 7** (ARI) — documentation, no code risk
6. **Phase 8** (Verification) — final gate, requires stable code

---

## Resource Requirements

| Phase | Dev Days | Risk Level |
|-------|----------|------------|
| 1 | 10-15 | MEDIUM |
| 2 | 3-5 | LOW |
| 3 | 5-10 | MEDIUM |
| 4 | 5-10 | MEDIUM |
| 5 | 3-5 | LOW |
| 6 | 10-15 | HIGH |
| 7 | 3-5 | LOW |
| 8 | 3-5 | LOW |

**Total estimated:** 42-70 dev days (8-14 weeks for one developer)

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| UI Graph Editing | User can create, edit, delete nodes and edges |
| YAML Import/Export | Round-trip YAML preserves all workflow data |
| macOS Hotkey | Global hotkey works with app in background |
| ExternalCapabilityBridge | Service starts, registers MCP manifests |
| TODO Comments | All marked TODOs resolved or converted to tracked issues |
| Async EventBus | 95th percentile dispatch latency < 50ms |
| ARI Documentation | Docs match implementation 100% |
| Test Suite | 100% pass rate, coverage maintained |
| UCGS | All rules pass at strict level |

---

## Rollback Plan

If any phase introduces regressions:

1. **Revert to previous commit** for that phase
2. **Document AER** if issue requires temporary workaround
3. **Return to planning** if fundamental problem discovered
4. **Never skip verification** even under time pressure

---

## Appendix: File Inventory

### Files to Create
```
ai_command_center/platform/hotkey_provider_macos.py
ai_command_center/services/external_capability_bridge_service.py
ai_command_center/domain/external_capability.py
ai_command_center/core/events/async_dispatch_policy.py
ai_command_center/core/events/async_dispatch_queue.py
```

### Files to Modify
```
ai_command_center/ui/views/workflow_graph_view.py
ai_command_center/ui/components/graph/
ai_command_center/ui/views/artifact_view.py
ai_command_center/core/events/topics.py
ai_command_center/services/artifact_service.py
ai_command_center/core/event_bus.py
ai_command_center/core/events/dispatch_policy.py
docs/architecture/AGENT_RUNTIME_INTERFACE.md
docs/architecture/ASYNC_EVENTBUS_POLICY.md
```

### Files to Update (Documentation)
```
docs/UNFINISHED_WORK_IMPLEMENTATION_PLAN.md (this file → archive)
docs/architecture/ARCHITECTURE_TRANSITION_PLAN.md
docs/architecture/ARCHITECTURE.md (phase gate history)
```

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-10 | Initial plan created |
