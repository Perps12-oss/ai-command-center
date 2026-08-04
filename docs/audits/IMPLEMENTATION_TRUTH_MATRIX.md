# Implementation Truth Matrix

**Milestone:** PHASE R1 — Runtime Reconciliation (+ Phase B UI surfaces)  
**Baseline:** `origin/main` @ `7d1065b`+ (R1 P5 Predictive/Undo ADR-014 — 2026-08-04)  
**Rule:** Exists ≠ Wired ≠ Authoritative  
**Plans:** `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md` · Phase B roadmap  
**Prior:** PHASE 0R matrix @ `e128a72` (superseded baseline; composition rows retained)

---

## Matrix

| Capability | Exists | Wired (composition root) | Tested | Live path? | Status | Evidence |
|------------|:------:|:------------------------:|:------:|:----------:|--------|----------|
| OperatorKernel | ✅ | ❌ | ⚠️ unit/golden only | ❌ bypassed | **PARTIAL** | `operator/kernel.py`; **not** in `service_factory.py` / `application.py`; ADR-006 → research only |
| GoalEngine | ✅ tree | ❌ | ✅ unit | ❌ | **RETIRED** | ADR-012 Accepted Option A; not in factory; live = `GoalRepository` + scheduler; cleanup optional |
| AgentCoordinator | ✅ | ❌ | ⚠️ orchestration tests | ❌ | **RETIRED** | ADR-013 Accepted; research/tests only; live = `AgentRuntimeService` |
| PlanningEngine | ✅ | ❌ | ⚠️ tests | ❌ | **RETIRED** | ADR-013 Accepted; research/tests only; live = `PlannerService` |
| ExternalCapabilityBridge | ✅ | ✅ | ✅ | ✅ | **WIRED** | `ExternalCapabilityBridgeService(bus)` in factory |
| BrainRuntime + WorldModel core | ✅ | ✅ | ✅ | ✅ | **WIRED** | `BrainRuntimeService(bus, world_model)` in factory |
| Predictive engine | ✅ | ❌ | ⚠️ package tests | ❌ | **RETIRED** | ADR-014 Accepted; research only; live blockers = Brain heuristics / SA-WM |
| Undo / replay | ✅ | ❌ | ⚠️ package tests | ❌ | **RETIRED** | ADR-014 Accepted; research only; live = TimelineService / SnapshotService / WM recover |
| ExecutionAuthority | ✅ | ✅ | ✅ | ✅ | **WIRED** | factory — canonical intake (ADR-006) |
| StateAuthority | ✅ | ✅ | ✅ | ⚠️ query+project+planner+WM node/edge mutate; goals SoT = scheduler | **PARTIAL** | Stage 2 soft-shadow closed (3a–6b + agents); WM mutate only; see `SHADOW_SOT_INVENTORY.md` |
| BaseGraphCanvas | ✅ | ✅ (UI) | ✅ | ✅ UI | **WIRED** (UI) | used by GraphCanvas, World Explorer, Graph Workspace |
| TimelineRenderer + ExecutionTimelineDock | ✅ | ✅ (UI) | ✅ | ✅ UI | **WIRED** (UI) | Ops / Agent Ops reuse |
| InspectorHost + InspectorDock | ✅ | ✅ (UI) | ✅ | ✅ UI | **WIRED** (UI) | universal kinds incl. `task` (not `plan_step`) |
| GlobalContextBar | ✅ | ✅ (UI shell) | ✅ | ✅ UI | **WIRED** (UI) | `global_context_bar.py` + `GlobalContextSnapshot` incl. active goal |
| OSPalette + provider registry | ✅ | ✅ (UI) | ✅ | ✅ UI | **WIRED** (UI) | `palette_provider.py`; Ctrl+K |
| Brain / Evidence / Operations / Graph / Insights views | ✅ | ✅ (UI) | ✅ | ✅ UI | **WIRED** (UI) | Phase B E06–E13 on main; Insights placeholder by plan |
| Cross-platform hotkey (macOS) | ✅ impl + ❌ live getter | ⚠️ placeholder returned | ⚠️ | ❌ stub path | **PARTIAL** | `get_hotkey_provider()` placeholder |
| Platform tray / notifications | ⚠️ stubs | ❌ | ❌ | ❌ | **MISSING/STUB** | `NotImplementedError` in `platform/platform_service.py` |
| Phase 5 Async EventBus (tiered + async queue) | ⚠️ policy only | ❌ | ⚠️ | ❌ | **PARTIAL** | `dispatch_policy.py` only; `tiered_dispatch_policy.py` / `async_dispatch_queue.py` **not** implemented — gated by Performance Investigation Report + human approval |

Legend: ✅ yes · ❌ no · ⚠️ incomplete / unit-only / stub

---

## Composition root registry (`service_factory.py`)

Registered = constructed in factory and started with other services.

| Component | Exists | Registered | Live EventBus role | R1 disposition |
|-----------|:------:|:----------:|--------------------|----------------|
| ExecutionAuthorityService | ✅ | ✅ | **Intake** — `UI_COMMAND` | **keep** (ADR-006) |
| StateAuthorityService | ✅ | ✅ | State projection before plan | **keep** — deepen per contract (P3) |
| SingleGoalScheduler | ✅ | ✅ | Goal queue → `EXECUTION_RUN_REQUEST` | **keep** |
| PlannerService | ✅ | ✅ | `PLAN_REQUEST` when not synthetic | **keep** |
| ExecutionOrchestratorService | ✅ | ✅ | Step execution | **keep** |
| ChatHandlerService | ✅ | ✅ | `LLM_STEP_REQUEST` handler | **keep** |
| RuntimeCapabilityRouterService | ✅ | ✅ | Classifier / provider map (not intake) | **keep** |
| OrchestrationService | ✅ | ✅ | Completion observer / receipts | **keep** |
| AgentRuntimeService | ✅ | ✅ | Agent plans / pipeline | **keep** |
| GoalEngine | ✅ | ❌ | — | **RETIRED (ADR-012 A)** — re-wire requires new ADR |
| OperatorKernel | ✅ | ❌ | — | **retire from live path** (ADR-006; research/tests only) |
| PlanningEngine | ✅ | ❌ | — | **RETIRED from live (ADR-013)** — research/tests only |
| AgentCoordinator | ✅ | ❌ | — | **RETIRED from live (ADR-013)** — live path = `AgentRuntimeService` |
| PredictiveEngine | ✅ | ❌ | — | **RETIRED from live (ADR-014)** — research/tests only |
| UndoReplay | ✅ | ❌ | — | **RETIRED from live (ADR-014)** — live = TimelineService / SnapshotService |

See `docs/audits/RUNTIME_AUTHORITY_MAP.md` for canonical vs paper paths.

### R1 priority status (2026-07-29)

| Priority | Gate | Status |
|----------|------|--------|
| P1 Runtime authority | ADR-006 | **PASSED** |
| P2 Composition / DI | Registry complete; keep rows registered; retire rows marked | **PASSED** (ADR-006/012/013/014 — Predictive/Undo retired from live) |
| P3 Event & state unification | State Authority Contract | **SOFT-SHADOW CLOSED** — 3a–6b + agents inventories; deepen SA mutate only with new ADR |
| P4 UI composition | Inspector/Graph/Timeline unify | **PASSED** — inspector rail (#138); graph unified; execution timeline disposition (#141) |
| P5 Feature completion | Predictive/Undo/platform | **INVENTORY CLOSED (ADR-014)** — packages research-only; live wire gated on new ADR; platform hotkey/tray still open |

---

## Phase B UI surfaces (program close-out)

| Surface | Slice | On main | Tom audit on main | Notes |
|---------|-------|:-------:|:-----------------:|-------|
| Canon consolidation | E00 | ✅ | ✅ `TOM_AUDIT_PR_UI_E00.md` | |
| Universal Inspector | E01 | ✅ | ✅ `TOM_AUDIT_PR_UI_E01.md` | kinds include `task` |
| Global Context Bar | E02 | ✅ | ✅ `TOM_AUDIT_PR_UI_E02.md` | active goal remediated Stage 1 |
| OS Palette | E03 | ✅ | ✅ `TOM_AUDIT_PR_UI_E03.md` | |
| Navigation Shell | E04 | ✅ | ✅ | |
| Memory / Brain / Goal / … / Insights | E05–E13 | ✅ | ✅ E04–E13 + package audit | E07 task inspect remediated Stage 1 |

**Phase B program COMPLETE:** ✅ on `main` via [#105](https://github.com/Perps12-oss/ai-command-center/pull/105) (`f03a4fa`, 2026-07-29).

---

## Critical pattern (OperatorKernel)

Expected authority path (paper / Phase 8):

```text
Application → service_factory → OperatorKernel → execution pipeline → receipt → verification
```

Observed (canonical — ADR-006):

```text
UI_COMMAND → ExecutionAuthority → GoalScheduler → [PlannerService] → ExecutionOrchestrator
           → ChatHandler / CapabilityRuntime / Tools → OrchestrationService → AppState
```

OperatorKernel remains **exists-but-not-wired**. Matrix status stays PARTIAL until explicitly retired from the tree or an ADR supersedes 006.

---

## Layer summary

| Layer | Maturity |
|-------|----------|
| UI surfaces / primitives | Ahead — Phase B E00–E13 WIRED at UI layer |
| Runtime authority services | Mixed (Goal/Brain/Authority WIRED; OperatorKernel/Coordinator/Predictive/Undo PARTIAL) |
| State Authority | WM mutate WIRED; Goals A; Memory 4b; Workflows 5a; Executions 6a |
| Documentation / plan COMPLETE claims | Must follow code on `main` — this matrix is the Exists/Wired probe |

---

## Update protocol

1. Change code on a branch from `main`.  
2. Re-run Exists / Wired / Tested probes against composition root.  
3. Update this matrix in the same PR as the wiring change.  
4. Only then adjust plan headers or archive under DOC_HYGIENE.

Guardian rejects “feature complete” PRs that do not update this matrix when they touch listed capabilities.
