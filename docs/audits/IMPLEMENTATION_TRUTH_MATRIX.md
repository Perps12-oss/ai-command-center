# Implementation Truth Matrix

**Milestone:** PHASE 0R — Repository Truth Reconciliation  
**Baseline:** `origin/main` @ `e128a72` (verified 2026-07-20)  
**Rule:** Exists ≠ Wired ≠ Authoritative  
**Plan:** `docs/plans/PHASE_0R_REPOSITORY_TRUTH_RECONCILIATION.md`

---

## Matrix

| Capability | Exists | Wired (composition root) | Tested | Live path? | Status | Evidence |
|------------|:------:|:------------------------:|:------:|:----------:|--------|----------|
| OperatorKernel | ✅ | ❌ | ⚠️ unit/golden only | ❌ bypassed | **PARTIAL** | `operator/kernel.py`; **not** in `service_factory.py` / `application.py`; tests `tests/test_operator/*` |
| GoalEngine | ✅ | ✅ | ✅ | ✅ | **WIRED** | constructed in `service_factory.py` (~L200); repo `SQLiteGoalEngineRepository` |
| AgentCoordinator | ✅ | ❌ | ⚠️ orchestration tests | ❌ | **PARTIAL** | `orchestration/agents/`; **not** in `service_factory.py` |
| PlanningEngine | ✅ | ❌ | ⚠️ tests | ❌ | **PARTIAL** | `orchestration/goals/planning_engine.py`; **not** in factory |
| ExternalCapabilityBridge | ✅ | ✅ | ✅ | ✅ | **WIRED** | `ExternalCapabilityBridgeService(bus)` in factory (~L208) |
| BrainRuntime + WorldModel core | ✅ | ✅ | ✅ | ✅ | **WIRED** | `BrainRuntimeService(bus, world_model)` in factory (~L198) |
| Predictive engine | ✅ | ❌ | ⚠️ package tests | ❌ | **PARTIAL** | `core/world_model/predictive_engine/`; **not** in factory |
| Undo / replay | ✅ | ❌ | ⚠️ package tests | ❌ | **PARTIAL** | `core/world_model/undo_replay/`; **not** in factory |
| ExecutionAuthority | ✅ | ✅ | ✅ | ✅ | **WIRED** | factory (~L268) |
| StateAuthority | ✅ | ✅ | ✅ | ✅ | **WIRED** | factory (~L262) |
| BaseGraphCanvas | ✅ | ✅ (UI) | ✅ | ✅ UI | **WIRED** (UI) | `ui/components/graph/base_graph_canvas.py`; used by `GraphCanvas`, World Model / relationship views |
| TimelineRenderer + ExecutionTimelineDock | ✅ | ✅ (UI) | ✅ | ✅ UI | **WIRED** (UI) | `timeline_renderer.py`, `execution_timeline_dock.py` |
| InspectorHost + InspectorDock | ✅ | ✅ (UI) | ✅ | ✅ UI | **WIRED** (UI) | universal rail; World Model also has `SelectionInspectorPanel` (compose, don’t fork) |
| Cross-platform hotkey (macOS) | ✅ impl + ❌ live getter | ⚠️ placeholder returned | ⚠️ | ❌ stub path | **PARTIAL** | `MacOSHotkeyProviderImpl` exists; `get_hotkey_provider()` returns placeholder `MacOSHotkeyProvider` |
| Platform tray / notifications | ⚠️ stubs | ❌ | ❌ | ❌ | **MISSING/STUB** | `NotImplementedError` in `platform/platform_service.py` |

Legend: ✅ yes · ❌ no · ⚠️ incomplete / unit-only / stub

---

## Composition root registry (`service_factory.py`)

Registered = constructed in factory and started with other services.

| Component | Exists | Registered | Live EventBus role |
|-----------|:------:|:----------:|-------------------|
| ExecutionAuthorityService | ✅ | ✅ | **Intake** — `UI_COMMAND` |
| StateAuthorityService | ✅ | ✅ | State projection before plan |
| SingleGoalScheduler | ✅ | ✅ | Goal queue → `EXECUTION_RUN_REQUEST` |
| PlannerService | ✅ | ✅ | `PLAN_REQUEST` when not synthetic |
| ExecutionOrchestratorService | ✅ | ✅ | Step execution |
| ChatHandlerService | ✅ | ✅ | `LLM_STEP_REQUEST` handler |
| RuntimeCapabilityRouterService | ✅ | ✅ | Classifier / provider map (not intake) |
| OrchestrationService | ✅ | ✅ | Completion observer / receipts |
| AgentRuntimeService | ✅ | ✅ | Agent plans / pipeline |
| GoalEngine | ✅ | ✅ | Goal persistence engine |
| OperatorKernel | ✅ | ❌ | — | **Non-canonical** (ADR-006) — research/tests only |
| PlanningEngine | ✅ | ❌ | — | Non-canonical until ADR supersedes 006 |
| AgentCoordinator | ✅ | ❌ | — | Non-canonical until wired + ADR |
| PredictiveEngine | ✅ | ❌ | — |
| UndoReplay | ✅ | ❌ | — |

See `docs/audits/RUNTIME_AUTHORITY_MAP.md` for canonical vs paper paths.

---

## Critical pattern (OperatorKernel)

Expected authority path:

```text
Application → service_factory → OperatorKernel → execution pipeline → receipt → verification
```

Observed:

```text
Tests → OperatorKernel
Application → service_factory → other services → execution
```

This is an **exists-but-not-wired** failure. Matrix status stays PARTIAL until factory + live command path use the kernel.

---

## Layer summary

| Layer | Maturity |
|-------|----------|
| UI surfaces / primitives | Ahead (many WIRED at UI layer) |
| Runtime authority services | Mixed (Goal/Brain/Authority WIRED; OperatorKernel/Coordinator/Predictive/Undo PARTIAL) |
| Documentation / plan COMPLETE claims | Historically ahead of both — corrected under DOC_HYGIENE + 0R |

---

## Update protocol

1. Change code on a branch from `main`.  
2. Re-run Exists / Wired / Tested probes against composition root.  
3. Update this matrix in the same PR as the wiring change.  
4. Only then adjust plan headers or archive under DOC_HYGIENE.

Guardian rejects “feature complete” PRs that do not update this matrix when they touch listed capabilities.
