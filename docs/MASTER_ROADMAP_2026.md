# AI Command Center — Master Roadmap 2026

**Generated:** 2026-07-11  
**Status:** ACTIVE  
**Authority:** `PROJECT_CONSTITUTION_V4.md`  
**Supersedes:** `ARCHITECTURE_TRANSITION_PLAN.md` (Programs 1-4), archived `UNFINISHED_WORK_IMPLEMENTATION_PLAN.md`

---

## Executive Summary

This document is the **single source of truth** for the AI Command Center development roadmap. It consolidates all prior program work into four coherent phases, identifies remaining deliverables, and provides clear exit criteria for each phase.

```text
Current State (2026-07-11)
═══════════════════════════════════════════════════════════════════════
✓ Programs 1-2: Stabilization & Enforcement     — COMPLETE
✓ Program 3: Workspace Adoption                 — COMPLETE
✓ Program 4 Slices 1-3: Platform Improvements  — COMPLETE
✓ Program 5 Phases A-D: Reasoning Layer MVP    — COMPLETE
⏳ Program 4 Slice 4: Phase 6 Async EventBus    — PARTIAL
⏳ Program 5 Phase E: External Integrations     — IN PROGRESS
⬜ Program 6: Multi-Agent Runtime               — GATED
⬜ Program 7: Knowledge Federation              — FUTURE
```

---

## Phase 1: Foundation Stabilization & Enforcement ✅

**Status:** COMPLETE (2026-07-03)

### Deliverables

| Item | Status | Evidence |
|------|--------|----------|
| S1 — Execution reliability | ✅ FIXED | Tool executor off UI thread, shutdown gaps closed |
| S2 — Shell & tool hardening | ✅ FIXED | Production sandbox + permission gate active |
| S3 — Model routing wire-up | ✅ FIXED | ModelRouterService registered in factory |
| S4 — UI runtime safety | ✅ FIXED | SystemView poll leak, Inspector UIQueue |
| S5 — State & lifecycle | ✅ FIXED | AppState/UI teardown wiring |
| S6 — Observability | ✅ FIXED | Topic counters active |
| S7 — Dependency cleanup | ✅ FIXED | Requirements.txt matches runtime imports |
| S8 — Ruff CI gate | ✅ ACTIVE | F821 / ruff continuous |

### Enforcement Active

| Stage | Status | Mechanism |
|-------|--------|-----------|
| E1 — Local warn | ✅ | `enforcement_mode: warn` |
| E2 — PR enforcement | ✅ | `profile: ai-command-center` |
| E3 — CI block | ✅ | `UCGS_ENFORCEMENT: block` |
| E4 — Constitutional gate | ✅ | `verify_constitution.py` |

---

## Phase 2: Workspace Adoption ✅

**Status:** COMPLETE (2026-07-06)

### Exit Gate Results

| Criterion | Target | Achieved |
|-----------|--------|----------|
| Workspace runtime influence | >60% | ✅ Achieved |
| Chat → consumer pattern | Complete | ✅ Complete |
| Entity graph integration | >50% | ✅ Achieved |

### Deliverables

| Item | Status | Evidence |
|------|--------|----------|
| W1 — Workspace routing | ✅ | `command_router` routes to workspace entities |
| W2 — Domain rehoming | ✅ | Chat projection in `workspace_state` |
| W3 — Bus-native workspace | ✅ | `WorkspaceOSService` bus-native |
| W4 — AppState domain split | ✅ | `chat_state`, `workspace_state`, `model_state`, `tool_state` |

---

## Phase 3: Platform Improvements ✅

**Status:** COMPLETE (2026-07-10)

### Deliverables

| Item | Status | Evidence |
|------|--------|----------|
| P1 — MSI Packaging | ✅ | `packaging/windows/` complete |
| P2 — Hotkey provider scaffold | ✅ | `platform/hotkey_provider.py` abstract base |
| P3 — Graph editing UI | ✅ | Edge creation, YAML import/export |
| P4 — Artifact viewer | ✅ | Live preview for supported kinds |

---

## Phase 4: Reasoning Layer MVP ✅

**Status:** COMPLETE (2026-07-10)

### Deliverables

| Phase | Status | Deliverable |
|-------|--------|-------------|
| A — Foundation | ✅ | `context_compiler.py`, `workspace_state` context priority |
| B — Capability facade | ✅ | `CapabilityPromptCatalogService` |
| C — Planner | ✅ | `PlannerService`, `plan.request` / `plan.generated` topics |
| D — Execution gates | ✅ | `ExecutionOrchestratorService`, approval tiers |
| E — External integrations | ✅ | `ExternalCapabilityBridgeService` scaffold |

---

## Phase 5: Async EventBus & Performance

**Status:** IN PROGRESS

**Priority:** HIGH  
**Estimated Effort:** 2-3 weeks  
**Dependencies:** Phase 1-4 complete ✅

### 5.1 Async Dispatch Policy

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

### 5.2 Dispatch Tiers

| Tier | Handler type | Dispatch mode | Examples |
|------|-------------|--------------|----------|
| R4a | UI updates | Immediate | `ui.*` |
| R4b | Tool execution | Queue (1 worker) | `tool.invoke`, `tool.cancel` |
| R4c | Heavy I/O | ThreadPool | `workflow.*`, `orchestration.*` |
| R4d | Model calls | Queue (dedicated) | `llm.request`, `llm.response` |

### 5.3 Migration Guide

**Deliverables:**
- [ ] Identify handlers requiring async dispatch
- [ ] Classify by dispatch tier
- [ ] Migration guide for service authors
- [ ] Performance benchmarks before/after

### 5.4 Exit Criteria

- [ ] 95th percentile dispatch latency < 50ms for R4a handlers
- [ ] No regression in existing tests (471 tests pass)
- [ ] Architecture lint clean
- [ ] UCGS PASS

---

## Phase 6: External Capability Bridge

**Status:** IN PROGRESS

**Priority:** HIGH  
**Estimated Effort:** 2-3 weeks  
**Dependencies:** Phase 4 Phase E scaffold ✅

### 6.1 MCP Integration Skeleton

**Deliverables:**
- [ ] MCP manifest schema in `runtime_manifests/mcp_manifest.py`
- [ ] MCP server connection handling (stubs for future)
- [ ] `mcp.capability.request` topic integration

**Note:** Full MCP wire-up remains future work. This phase creates the scaffold only.

### 6.2 Capability Aggregation

**Deliverables:**
- [ ] Integration with `CapabilityPromptCatalogService`
- [ ] Aggregate external capabilities into planner-facing catalog
- [ ] Bus topics documented in `topics.py`

### 6.3 External Provider Manifests

**Deliverables:**
- [ ] Load manifests from `runtime_manifests/`
- [ ] Validate manifest schema
- [ ] Publish `external.capability.registered` topic

### 6.4 Exit Criteria

- [ ] `ExternalCapabilityBridgeService` starts successfully
- [ ] Unit tests for manifest loading
- [ ] Integration tests for capability aggregation
- [ ] Architecture lint clean

---

## Phase 7: Operational Intelligence

**Status:** COMPLETE (foundation)  
**Priority:** HIGH  
**Estimated Effort:** Done  
**Dependencies:** Phase 1-4 complete ✅

### 7.1 Trust & Execution Foundation

**Already implemented:**
- `ExecutionOrchestratorService` — execution gates with approval tiers
- `TruthBoundary` — validation before response
- `orchestration/execution/executor.py` — provider execution with receipts

### 7.2 Constitutional Guarantees

**Already enforced:**
- Intent → Provider → Receipt → Composer pipeline
- No LLM hallucination without provider verification
- Execution receipts required for all orchestration operations

### 7.3 Exit Criteria

✅ Phase 7 foundational work complete (trust before abstraction)

---

## Phase 8: Operator Kernel & Model Independence

**Status:** PLANNED  
**Priority:** HIGH  
**Estimated Effort:** 6-8 weeks  
**Dependencies:** Phase 7 complete ✅, Phase 5 (Async) ✅

### 8.1 Mission

Transform ACC from **Operator Runtime** into **Model-Agnostic Operator Platform**.

**Core Principle:**
```
Behavior belongs to ACC
Reasoning belongs to LLM
```

### 8.2 Architecture

```
                USER
                  │
                  ▼
        ┌─────────────────┐
        │ Operator Kernel │
        └────────┬────────┘
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
    Intent    Planning   Policies
      └──────────┼──────────┘
                 ▼
      Prompt Assembly Service
                 ▼
          Model Adapter
                 ▼
        GPT Claude Qwen DeepSeek Gemini
                 ▼
        Compliance Engine
                 ▼
        Response Contract
                 ▼
         UI Renderer
```

### 8.3 Major Subsystems

| Subsystem | Purpose |
|-----------|---------|
| **OperatorKernel** | Single source of operational behavior |
| **IntentResolver** | Classify user intent |
| **ModeResolver** | Determine operator mode |
| **PolicyEngine** | Enforce constitutional rules |
| **PromptAssemblyService** | Dynamic prompt construction |
| **ModelAdapter** | Provider-neutral interface |
| **ComplianceEngine** | Validate responses, detect hallucinations |

### 8.4 Model Adapter Layer

**Package:** `ai_command_center/models/`

```
base.py              — ModelAdapter contract
openai_adapter.py   — OpenAI / Azure OpenAI
anthropic_adapter.py — Claude
gemini_adapter.py    — Gemini
ollama_adapter.py   — Local models
registry.py          — Model registry
```

**Every adapter returns:**
```python
ModelResponse  # ACC never consumes raw model output
```

### 8.5 Structured Response Contracts

| Mode | Contract |
|------|----------|
| Chat | `ChatResponse` |
| Command | `CommandResponse` |
| Investigation | `InvestigationResponse` |
| Architect | `ArchitectResponse` |

**No free-form operational responses.**

### 8.6 Compliance Engine

**Validates every response:**
- Hallucinated capabilities
- Invalid providers
- Missing evidence
- Contract violations
- Forbidden claims

### 8.7 Success Criteria

- [ ] Swap models without UI changes
- [ ] Swap models without prompt rewrites
- [ ] Swap models without capability changes
- [ ] Same command behavior across providers
- [ ] Compliance catches hallucinations
- [ ] Operator identity remains consistent

### 8.8 Deliverables

```
ai_command_center/operator/
├── __init__.py
├── kernel.py
├── intent_resolver.py
├── mode_resolver.py
├── policy_engine.py
├── prompt_assembly.py
├── compliance_engine.py
└── response_contracts.py

ai_command_center/models/
├── __init__.py
├── base.py
├── adapter.py
├── adapters/
│   ├── __init__.py
│   ├── openai_adapter.py
│   ├── anthropic_adapter.py
│   ├── gemini_adapter.py
│   └── ollama_adapter.py
└── registry.py

tests/operator/
├── test_kernel.py
├── test_intent_resolver.py
├── test_model_adapters.py
├── test_compliance_engine.py
└── test_model_independence.py
```

---

## Phase 9: Goals, Planning & Multi-Agent Coordination

**Status:** PLANNED  
**Priority:** HIGH  
**Estimated Effort:** 8-10 weeks  
**Dependencies:** Phase 8 (Operator Kernel) ✅

### 9.1 Mission

Transform ACC from **Command Execution System** into **Goal Driven Workspace OS**.

**Core Principle:**
```
Commands are temporary.
Goals persist.
```

### 9.2 Architecture

```
Goal
  │
  ▼
Planner
  │
  ▼
Task Graph
  │
  ▼
Execution Coordinator
  │
  ▼
Specialist Agents
  │
  ▼
Timeline
```

### 9.3 Major Subsystems

| Subsystem | Purpose |
|-----------|---------|
| **GoalEngine** | Persistent goal entities |
| **PlanningEngine** | Goal → ExecutionPlan |
| **TaskGraph** | DAG-based task management |
| **AgentContracts** | Capability declarations |
| **AgentCoordinator** | Task assignment, conflict resolution |
| **PolicyEngine** | Pre-execution approval gates |
| **OperationalMemory** | Timeline-based memory |

### 9.4 Planning Pipeline

```
Goal → Explore → Plan → Validate → Execute → Review → Close
```

### 9.5 Agent Contract Framework

Every agent declares:
```python
Capabilities
Permissions
Dependencies
Risk Level
Evidence Requirements
```

### 9.6 Success Criteria

- [ ] ACC manages long-running goals
- [ ] Plans survive restarts
- [ ] Multiple agents collaborate
- [ ] Operator remains authority
- [ ] Every agent action is auditable
- [ ] Goal progress visible in UI

### 9.7 Deliverables

```
ai_command_center/orchestration/goals/
├── __init__.py
├── goal_engine.py
├── goal.py
├── planning_engine.py
├── task_graph.py
├── task.py
└── agent_coordinator.py

ai_command_center/orchestration/agents/
├── __init__.py
├── agent_contract.py
├── agent_registry.py
└── policy_engine.py

tests/orchestration/goals/
├── test_goal_engine.py
├── test_task_graph.py
├── test_planning_pipeline.py
└── test_agent_coordination.py
```

---

## Phase 10: Workspace OS Intelligence & World Model Expansion

**Status:** FUTURE  
**Priority:** MEDIUM  
**Estimated Effort:** 10-12 weeks  
**Dependencies:** Phase 9 (Goals & Multi-Agent) ✅

### 10.1 Mission

Transform ACC from **Goal Based System** into **Workspace Operating System**.

**Core Principle:**
```
The system no longer reasons primarily from conversations.
It reasons from:
  - Entities
  - Relationships
  - State
  - Events
```

### 10.2 Architecture

```
World Model
     │
     ▼
Entity Graph
     │
     ▼
Relationship Engine
     │
     ▼
State Projection Layer
     │
     ▼
Reasoning Engine
     │
     ▼
Operator
```

### 10.3 Major Subsystems

| Subsystem | Purpose |
|-----------|---------|
| **WorldModelService** | Core entity storage (Projects, Files, Notes, Tasks, Goals, Agents) |
| **EntityGraph** | Graph database style architecture |
| **RelationshipEngine** | Tracks ownership, dependencies, history |
| **StateProjectionLayer** | CQRS-style read models |
| **ContextEngine** | Entity-based context assembly |
| **PredictiveOperations** | Proactive suggestions |
| **UndoReplayFramework** | Timeline-powered recovery |

### 10.4 World Explorer UI

Similar to:
- Obsidian Graph
- Neo4j Browser
- VS Code Explorer

Displays:
```
Entities
Relationships
Dependencies
Goals
Agents
```

### 10.5 Success Criteria

- [ ] ACC reasons from world state instead of conversation history
- [ ] Every object is an entity
- [ ] Relationships are queryable
- [ ] Goals, tasks, agents, files, projects are connected
- [ ] Context is generated from the World Model
- [ ] Undo and replay are operational
- [ ] ACC proactively identifies blockers and opportunities
- [ ] Workspace OS behavior driven by entities, events, and state

### 10.6 Deliverables

```
ai_command_center/world/
├── __init__.py
├── world_model_service.py
├── entity_graph.py
├── relationship_engine.py
├── state_projections.py
├── context_engine.py
├── predictive_engine.py
└── undo_replay.py

ai_command_center/ui/views/
├── world_explorer_view.py
├── relationship_visualizer.py
└── dependency_inspector.py

tests/world/
├── test_world_model.py
├── test_entity_graph.py
├── test_relationships.py
├── test_state_projections.py
└── test_context_engine.py
```

---

## Phase 11: Cross-Platform Expansion

**Status:** FUTURE

**Priority:** MEDIUM  
**Estimated Effort:** 8-12 weeks  
**Dependencies:** Phase 5 (Async), Phase 10 (World Model)

### 11.1 macOS Support

**Deliverables:**
- [ ] `platform/hotkey_provider_macos.py` (CGEvent tap)
- [ ] Accessibility permissions check and user prompt
- [ ] System tray parity with Windows

### 11.2 Linux Support

**Deliverables:**
- [ ] X11/Wayland hotkey detection
- [ ] System tray integration (libappindicator)
- [ ] Path handling for Linux filesystem

### 11.3 Platform Abstraction

**Deliverables:**
- [ ] Unified `PlatformService` abstraction
- [ ] Platform-specific overrides via config
- [ ] Cross-platform test automation

---

## Implementation Order

```
Phase 7 → Phase 8 → Phase 9 → Phase 10 → Phase 11
   │         │         │         │         │
   ▼         ▼         ▼         ▼         ▼
Complete  Operator   Goals &   World     Cross-
(Founda-   Kernel    Multi-   Model    Platform
tion)      (Model    Agent    (Entity
           Indep)    Coord)    Graph)
```

**Rationale:**
1. **Phase 7** (Complete) — Trust before abstraction
2. **Phase 8** (Operator Kernel) — Abstraction before agents
3. **Phase 9** (Goals & Multi-Agent) — Agents before world-model
4. **Phase 10** (World Model) — World-model for true Workspace OS
5. **Phase 11** (Platform) — Independent, benefits from all prior phases

---

## Verification Gates

All phases require:

1. **Pre-flight:** `python3 scripts/verify_constitution.py`
2. **Lint:** `python3 -m ruff check ai_command_center`
3. **Tests:** `python3 -m pytest -m "not slow"` (all pass)
4. **Arch lint:** `python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json`
5. **UCGS:** `python3 tools/ucgs_runner.py > .ucgs_last.yaml && python3 tools/ucgs_ci_gate.py .ucgs_last.yaml`

---

## Resource Requirements

| Phase | Dev Weeks | Risk Level | Priority |
|-------|-----------|------------|----------|
| 7 — Operational Intelligence | Done | — | HIGH |
| 8 — Operator Kernel | 6-8 | HIGH | HIGH |
| 9 — Goals & Multi-Agent | 8-10 | HIGH | HIGH |
| 10 — World Model | 10-12 | MEDIUM | MEDIUM |
| 11 — Cross-Platform | 8-12 | MEDIUM | LOW |

**Total remaining:** 32-42 weeks (one developer)

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Phase 8 — Model Independence | Swap models without prompt rewrites |
| Phase 9 — Goals | Plans survive restarts, multiple agents collaborate |
| Phase 10 — World Model | ACC reasons from entities, not conversation |
| Phase 11 — Cross-Platform | macOS + Linux hotkey + tray parity |
| Test Suite | 100% pass rate maintained |
| UCGS | All rules pass at strict level |

---

## Rollback Plan

If any phase introduces regressions:

1. **Revert to previous commit** for that phase
2. **Document AER** if issue requires temporary workaround
3. **Return to planning** if fundamental problem discovered
4. **Never skip verification** even under time pressure

---

## Appendix: Consolidated Reference

### Superseded Documents

| Document | Replaced by |
|----------|-------------|
| `ARCHITECTURE_TRANSITION_PLAN.md` | This document |
| `UNFINISHED_WORK_IMPLEMENTATION_PLAN_2026-07-11_COMPLETE.md` | This document (Phase 1-4 summary) |

### Active Reference Documents

| Document | Role |
|----------|------|
| `PROJECT_CONSTITUTION_V4.md` | Supreme authority |
| `AGENTS.md` | Layer ownership rules |
| `docs/ARCHITECTURE.md` | Runtime architecture |
| `docs/architecture/WORKSPACE_VISION.md` | Product north star |
| `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md` | **Active** — runtime reconciliation (strict priority order) |
| `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md` | **Accepted** — ExecutionAuthority canonical |
| `docs/architecture/STATE_AUTHORITY_CONTRACT.md` | **Active** — next architectural work |
| `docs/plans/PHASE_0R_REPOSITORY_TRUTH_RECONCILIATION.md` | Superseded by R1 |
| `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md` | Exists / Wired / Tested matrix |
| `docs/plans/PHASE_5_ASYNC_EVENTBUS_PLAN.md` | Phase 5 (PARTIAL — keep active) |
| `docs/plans/PHASE_6_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md` | Phase 6 (PARTIAL — keep active) |
| `docs/archive/PHASE_7_MULTI_AGENT_RUNTIME_PLAN_SUPERSEDED.md` | Phase 7 (archived SUPERSEDED) |
| `docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md` | Phase 8 (PARTIAL — keep active) |
| `docs/plans/PHASE_9_GOALS_MULTI_AGENT_PLAN.md` | Phase 9 (PARTIAL — keep active) |
| `docs/plans/PHASE_10_WORLD_MODEL_PLAN.md` | Phase 10 (PARTIAL — keep active) |
| `docs/plans/PHASE_9_CROSS_PLATFORM_PLAN.md` | Cross-platform / roadmap Phase 11 (NOT_COMPLETE) |
| `docs/governance/DOC_HYGIENE.md` | Active vs archive doc rules |
| `docs/audits/PHASE_PLANS_ARCHIVE_VERIFICATION.md` | Code verification before archive |

### Active Governance

| Document | Role |
|----------|------|
| `governance/CONSTITUTIONAL_LEDGER.md` | Amendment history |
| `governance/constitutional_preflight.md` | Pre-flight checklist |
| `ucgs.config.yaml` | Enforcement configuration |
| `ucgs.profiles/ai-command-center.yaml` | Project profile |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial consolidated roadmap — Phases 1-4 complete, Phases 5-9 planned |
| 2026-07-11 | Updated Phases 7-11 with Operator Kernel, Goals & Multi-Agent, World Model designs |
