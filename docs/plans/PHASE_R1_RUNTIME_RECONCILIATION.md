# PHASE R1 — Runtime Reconciliation

**Status:** ACTIVE — **blocks** Phase B UI expansion and Phase 8–10 feature completion  
**Supersedes:** `PHASE_0R_REPOSITORY_TRUTH_RECONCILIATION.md` (same intent, strict priority order)  
**Baseline:** `origin/main`  
**Authority:** Constitution · `DOC_HYGIENE.md` · `REPOSITORY_TRUTH_CANON.md` · `RUNTIME_AUTHORITY_MAP.md`

---

## Principle

Do **not** bridge all gaps as one effort. Gap categories caused repository drift; R1 fixes them **in order**.

```text
Priority 1  Runtime authority (what ACC actually is)
Priority 2  Composition root (exists → registered → reachable)
Priority 3  Event & state unification (single SoT model)
Priority 4  UI composition (converge primitives)
Priority 5  Feature completion (predictive, undo, platform)
```

**No Priority N+1 work until Priority N decision gate passes.**

---

## Priority 1 — Runtime Authority Migration

**Highest value.** Determines what ACC actually is.

### Verified live path (see `docs/audits/RUNTIME_AUTHORITY_MAP.md`)

```text
UI_COMMAND → ExecutionAuthority → GoalScheduler → [PlannerService] → ExecutionOrchestrator
           → ChatHandler / CapabilityRuntime / Tools → OrchestrationService → AppState
```

### Paper path (Phase 8 plan, not wired)

```text
OperatorKernel → PlanningEngine → AgentCoordinator → RuntimeCapabilityRouter → Provider
```

### Decision gate (human + Guardian sign-off **before coding**)

| # | Question | Status |
|---|----------|--------|
| 1 | Is **OperatorKernel** the intended runtime authority, or is **ExecutionAuthority** canonical? | ✅ **ExecutionAuthority** — ADR-006 |
| 2 | Is **PlanningEngine** mandatory for all requests or goal-oriented only? | ✅ **RETIRED from live (ADR-013)** — live = `PlannerService` |
| 3 | Does **AgentCoordinator** sit under OperatorKernel or beside **AgentRuntimeService**? | ✅ **RETIRED from live (ADR-013)** — live = `AgentRuntimeService` |
| 4 | What is the **single** canonical execution graph? | ✅ **ExecutionAuthority** intake — documented in `ARCHITECTURE.md` + ADR-006 |

**Forbidden:** wiring OperatorKernel into factory while ExecutionAuthority remains intake (ADR-006).

### R1.1 exit criteria

- [x] Authority decision recorded — **ADR-006 (Answer A)**  
- [x] `docs/ARCHITECTURE.md` shows one canonical execution graph  
- [x] OperatorKernel demoted in plans (research only — ADR-006; banners on Phase 8/9 / ORDER)  
- [x] Tom audit: no dual authority path in new PRs *(ongoing gate — ADR-006 enforced)*  

### R1.1 — **GATE PASSED** (2026-07-21)

Next architectural battle: **Runtime Authority vs State Authority** — not ExecutionAuthority vs OperatorKernel.

See `docs/architecture/STATE_AUTHORITY_CONTRACT.md`.

---

## Priority 2 — Dependency Injection & Composition

Recurring failure mode:

```text
Component exists → not created → not registered → not reachable
```

### Deliverable

Maintain **Composition Root Registry** in `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md` (Composition section).

Every major subsystem: **Registered Yes/No** in `service_factory.py` + reachable from startup.

| Component | Registered on main | R1 target |
|-----------|:------------------:|-----------|
| ExecutionAuthority | ✅ | keep |
| ExecutionOrchestrator | ✅ | keep |
| PlannerService | ✅ | keep or merge per P1 |
| OperatorKernel | ❌ | wire **or** retire |
| PlanningEngine | ❌ | **RETIRED from live (ADR-013)** |
| AgentCoordinator | ❌ | **RETIRED from live (ADR-013)** |
| PredictiveEngine | ❌ | P5 unless P1 mandates |
| UndoReplay | ❌ | P5 unless P1 mandates |

**Rule:** No subsystem may exist only outside the composition root after R1.2.

### R1.2 exit criteria

- [x] Registry complete for all authority + orchestration components *(truth matrix 2026-07-29)*  
- [x] Every “keep” row is factory-registered  
- [x] Every “retire” row removed or marked deprecated with migration note — OperatorKernel (ADR-006); GoalEngine (ADR-012 A); PlanningEngine / AgentCoordinator (ADR-013). Predictive/Undo remain **P5** (not R1.2 retire-or-wire for Stage 2).

**P2 status:** **CLOSED** for Stage 2 authority rows (ADR-006/012/013). PredictiveEngine / UndoReplay stay P5.

---

## Priority 3 — Event & State Unification

**Active next workstream** after ADR-006 (authority decided).

Subsystems: Goals, Agents, Executions, World Model, Timeline, Approvals.

Target model:

```text
Workspace State → State Authority (contract) → Context Projection → Planner
       → Execution (ExecutionAuthority) → State Mutation → AppState → UI
```

**Primary artifact:** `docs/architecture/STATE_AUTHORITY_CONTRACT.md`

### R1.3 questions

- What is the single source of truth for workspace/runtime state?  
- Which isolated state caches must merge into AppState reducers?  
- Do `GoalEngine` and `SingleGoalScheduler` converge or divide with explicit boundaries?

### R1.3 exit criteria

- [x] State ownership table published *(contract § Backing systems — 2026-07-30)*  
- [x] No UI or service maintains *undocumented* shadow SoT for listed domains *(Stage 2 inventories closed: Goals ADR-012 A; Memory 4a–4c; Workflows 5a+5b; Executions 6a+6b; Agents ADR-013 — soft duals documented, not silent-merged)*  
- [x] Event topics documented for cross-subsystem flows *(contract § Event topics — SA surface; mutate node+edge)*
- [x] Goals dual-path inventory + disposition *(ADR-012 Accepted Option A)*
- [x] Memory soft-shadow inventory *(4a–4c)*
- [x] Workflows soft-shadow inventory *(5a+5b keep execution-scoped)*
- [x] Executions soft-shadow inventory *(6a+6b correlation)*
- [x] Agents soft-shadow + PlanningEngine/AgentCoordinator disposition *(ADR-013)*

**P3 Stage 2 soft-shadow status:** **CLOSED** (ungated). Remaining: optional SA mutate for non-WM domains (gated by ADR); Goose = Stage 3.
---

## Priority 4 — UI Composition

**Closed** for Stage 2 / Phase B residuals (#138 inspector rail; timeline
disposition). Foundations on `main`.

Devin/Cursor inventory: foundations on `main` — `BaseGraphCanvas`, `TimelineRenderer`, `GoalView`, `AgentsView`, `ExecutionsView`, `WorldExplorerView`, `SelectionInspectorPanel` (hosted on `InspectorDock`).

Convergence targets:

```text
SelectionInspectorPanel → compose into → InspectorHost → InspectorDock
All graph views → shared BaseGraphCanvas + selection model
```

### R1.4 exit criteria

- [x] One inspector rail (no third product inspector OS) — World/Graph use `InspectorDock`; Art. 12 selection is `world_node` on that rail  
- [x] One graph engine (`BaseGraphCanvas` adapters only)  
- [x] One **execution** timeline stack (`TimelineRenderer` + dock) — Mission Control `ActivityTimeline` retained as secondary multi-domain **activity feed** (not a scrubber engine); see `docs/audits/R1_P4_TIMELINE_DISPOSITION.md`
---

## Priority 5 — Feature Completion

Only after runtime authority is settled:

- PredictiveEngine  
- UndoReplay  
- Cross-platform hotkeys / tray  
- Advanced agent workflows  

Otherwise features complete off the wrong execution path.

---

## R1 program exit (merge-ready)

| Area | Criterion |
|------|-----------|
| **Authority** | OperatorKernel **adopted or officially retired**; exactly one intake/execution story |
| **Composition** | All core services registered through composition root |
| **State** | Workspace / World Model / AppState model authoritative |
| **UI** | Inspector, Timeline, Graph unified |
| **Documentation** | Every active plan reflects runtime reality |

---

## Roles

| Actor | R1 responsibility |
|-------|---------------------|
| **You** | Authority decision (P1 gate) |
| **Devin** | Wiring/migration **after** gate; no feature sprawl |
| **Cursor / Tom** | Evidence audits; reject dual-path PRs |

---

## References

| Doc | Role |
|-----|------|
| `docs/audits/RUNTIME_AUTHORITY_MAP.md` | Live vs paper paths |
| `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md` | Exists / Wired / Tested |
| `docs/audits/REPOSITORY_TRUTH_CANON.md` | UI inventory SoT |
| `docs/governance/DOC_HYGIENE.md` | Archive gate |
