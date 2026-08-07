# Phase Plans Archive Verification

**Date:** 2026-07-20  
**Baseline:** `origin/main` @ `e128a72` (guardian branch tip includes docs-only Canon commits)  
**Authority:** `docs/governance/DOC_HYGIENE.md`, `docs/governance/PHASE_COMPLETION_RULE.md`  
**Method:** Extract plan exit criteria → verify paths / wiring / stubs in code. Plan status tables ignored.

---

## Verdict

| Plan | Code verdict | Archive as COMPLETE? | Archive other class? |
|------|--------------|----------------------|----------------------|
| `PHASE_5_ASYNC_EVENTBUS_PLAN.md` | COMPLETE | **YES** (after this PR merges) | Archive after merge to `main` |
| `PHASE_6_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md` | PARTIAL | **NO** | Keep active |
| `PHASE_7_MULTI_AGENT_RUNTIME_PLAN.md` | NOT_COMPLETE (GATED / abandoned layout) | **NO** | **YES → SUPERSEDED** |
| `PHASE_8_OPERATOR_KERNEL_PLAN.md` | PARTIAL (library + tests; not live intake) | **NO** | Keep active |
| `PHASE_8_KNOWLEDGE_FEDERATION_PLAN.md` | NOT_COMPLETE | **NO** | Keep active |
| `PHASE_9_GOALS_MULTI_AGENT_PLAN.md` | PARTIAL | **NO** | Keep active |
| `PHASE_9_CROSS_PLATFORM_PLAN.md` | NOT_COMPLETE (stubs) | **NO** | Keep active |
| `PHASE_10_WORLD_MODEL_PLAN.md` | PARTIAL | **NO** | Keep active |
| `PHASE_7_8_9_10_QA.md` | Docs Q&A | N/A | Keep active |
| `IMPLEMENTATION_ORDER.md` | Ordering only | N/A | Keep active |
| `REMAINING_IMPLEMENTATION_PLAN.md` | STALE / false COMPLETE matrix | **NO as COMPLETE** | **YES → STALE** |

**Zero Phase 5–10 plans verified COMPLETE_ON_MAIN.**

---

## Evidence (blocking gaps)

### Phase 5 — Async EventBus — COMPLETE (code on this train)

| Present | Notes |
|---------|-------|
| `dispatch_policy.py` (ABC + Sync), `tiered_dispatch_policy.py`, `async_dispatch_queue.py` | Multi-pool R4b/R4c/R4d |
| `event_bus.py` tiered path; `create_application()` enables `tiered_dispatch=True` | Bare `EventBus()` remains sync |
| Tests: `test_tiered_dispatch_policy.py`, `test_async_dispatch_queue.py` (+ existing R4b/R4c) | Isolation + R4a p95 &lt; 50ms |
| UCGS profile `dispatch_policy.pools` | Matches DEFAULT_POOL_CONFIGS |
| Investigation + approval | `PERF_PHASE5_ASYNC_EVENTBUS_INVESTIGATION.md` |

### Phase 6 — External Capability Bridge — PARTIAL

| Present | Missing / incomplete |
|---------|----------------------|
| `services/external_capability_bridge_service.py`, `runtime_manifests/mcp_manifest.py`, `orchestration/providers/mcp_*.py` | Plan’s `plugins/runtime_manifests/mcp_manifest.py` / directory MCP scan; `runtime/mcp_runtime_provider.py` as named |
| Tests: `tests/test_external_capability_bridge_service.py`, `tests/runtime_manifests/test_mcp_manifest.py` | Full “manifests load from runtime_manifests/” MCP exit as written |

### Phase 7 — Multi-Agent Runtime — NOT_COMPLETE → archive SUPERSEDED

| Plan-named deliverable | On main? |
|------------------------|----------|
| `services/agent_registry_service.py` | **NO** |
| `services/agent_context_service.py` | **NO** |
| `services/agent_task_executor_service.py` | **NO** |
| `services/agent_verification_service.py` | **NO** |
| Constitutional gate checklist in plan | unchecked |

Related but different design: `services/agent_runtime_service.py`, Phase 9 `orchestration/agents/*`.  
Index already marked Superseded. Safe to archive as **SUPERSEDED**, not COMPLETE.

### Phase 8 — Operator Kernel — PARTIAL

| Present | Gap |
|---------|-----|
| `operator/kernel.py`, resolvers, compliance, adapters under `models/adapters/` | `OperatorKernel` **not** wired in `service_factory.py` / application intake |
| `tests/test_operator/*` | Live model-agnostic product path; `gemini_adapter.py`; plan’s independence score gate |

`rg OperatorKernel` outside `operator/` hits **tests only**.

### Phase 8 — Knowledge Federation — NOT_COMPLETE

| Present | Missing |
|---------|---------|
| `services/federation_service.py`, World Model `knowledge_graph_panel.py` | `knowledge_query_service.py`, `knowledge_index_service.py`, `ui/views/knowledge_graph_view.py`, vector/query topics as planned |

### Phase 9 — Goals & Multi-Agent — PARTIAL (research vs live)

| Present | Gap / disposition |
|---------|-------------------|
| Live goals = `GoalRepository` + `SingleGoalScheduler` in factory | Phase-9 `GoalEngine` **RETIRED from live (ADR-012 A)** — tree may remain for unit tests |
| Live agents = `AgentRuntimeService`; live planning = `PlannerService` | `AgentCoordinator` / `PlanningEngine` **RETIRED from live (ADR-013)** |
| UI `goal_dashboard/` | Plan exit: plans survive restarts + live multi-agent collaboration as specified — backlog |
| | `agent_policy_engine.py` / `agent_spawner.py` / `agent_lifecycle.py` absent |

### Phase 9 Cross-Platform (roadmap “Phase 11 platform”) — NOT_COMPLETE

| Present | Gap |
|---------|-----|
| `platform/platform_service.py`, `platform/macos/hotkey_provider.py` (`MacOSHotkeyProviderImpl`) | `get_hotkey_provider()` still returns **placeholder** `MacOSHotkeyProvider` (`hotkey_provider.py`) |
| Working `ui/tray.TrayController` + pystray path | Widespread `NotImplementedError` for tray/notifications/window APIs in `platform_service.py` |
| | **Not an R1 blocker** — Phase 11 backlog (`R1_UNGATED_STOP_LINE.md`) |

### Phase 10 — World Model — PARTIAL (core live; predictive/undo research)

| Present | Gap / disposition |
|---------|-------------------|
| `core/world_model/`, Brain wiring, UI world explorer / panels; SA WM mutate | PredictiveEngine / UndoReplay **RETIRED from live (ADR-014)** — research/unit tests only |
| Live timeline undo / snapshots via TimelineService / SnapshotService / WM recover | Do not factory-wire predictive/undo without ADR superseding 014 |
| Tests under `tests/core/world_model/` and `tests/ui/test_world_model_*` | Product wire of predictive/undo exit criteria — gated |

### `REMAINING_IMPLEMENTATION_PLAN.md` — STALE

Claims Phase 5/6/8/9/10/11 Cross-Platform **COMPLETE**. Code evidence above contradicts several of those claims. Archive as **STALE** with `Do-not-plan-from: true`.

---

## Naming conflict (do not collapse)

| Label | Meaning |
|-------|---------|
| Phase 11 (roadmap / `PHASE_9_CROSS_PLATFORM_PLAN.md`) | macOS/Linux platform expansion — **incomplete** |
| Phase 11 frontend (`docs/PHASE_11_FRONTEND_IMPLEMENTATION.md`) | UI workspaces 11A–11F — largely **on main** (see Canon) |

---

## Actions taken under this audit

1. Added `docs/governance/DOC_HYGIENE.md`.
2. Archived **only**:
   - Phase 7 plan → `docs/archive/PHASE_7_MULTI_AGENT_RUNTIME_PLAN_SUPERSEDED.md`
   - Remaining implementation plan → `docs/archive/REMAINING_IMPLEMENTATION_PLAN_2026-07-12_STALE.md`
3. Left Phase 5, 6, 8, 9, 10 plans in `docs/plans/` as PARTIAL / NOT_COMPLETE.
4. Updated `docs/plans/README.md` to match code verification.

No plan archived as COMPLETE.
