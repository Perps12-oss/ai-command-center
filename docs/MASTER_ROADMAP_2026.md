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

## Phase 7: Multi-Agent Runtime

**Status:** GATED

**Priority:** MEDIUM  
**Estimated Effort:** 4-6 weeks  
**Dependencies:** Phase 5 (Async), Phase 6 (External Bridge)

### 7.1 Constitutional Gate Checklist

Before any multi-agent code:

- [ ] **A1 — Context Before Conversation**: Which service owns agent context assembly?
- [ ] **A2 — Execution Before Explanation**: Minimum executable artifact before `chat.complete`?
- [ ] **A5 — Determinism Before AI**: Deterministic fallback when agent fails?
- [ ] **System-level**: Multi-agent opt-in; `CommandRouterService` not shadowed

### 7.2 Required Deliverables

1. [ ] Data-flow diagram: spawn → context → execute → result
2. [ ] EventBus topics + payloads (new or existing)
3. [ ] Service decomposition diagram
4. [ ] Constitutional question → design decision mapping
5. [ ] Forbidden execution paths list
6. [ ] Verification plan (tests, scripts, gates)

### 7.3 Ownership Rules

```text
UI → AppState → EventBus → Services → Repositories → Storage
```

- No agent direct access to files, SQLite, settings, Ollama, or tools
- No direct service-to-service calls
- No global state — `AppState` + `SettingsSnapshot` only

### 7.4 Agent Lifecycle

| Event | Topic | Payload |
|-------|-------|---------|
| Spawn | `agent.spawned` | `{ agent_id, config, workspace_scope }` |
| Context request | `agent.context.request` | `{ agent_id, scope }` |
| Context result | `agent.context.result` | `{ agent_id, context_bundle }` |
| Task assigned | `agent.task.assigned` | `{ agent_id, task_id, capability }` |
| Task complete | `agent.task.completed` | `{ agent_id, task_id, result }` |
| Terminate | `agent.terminated` | `{ agent_id, reason }` |

### 7.5 Exit Criteria

- [ ] Constitutional gate sign-off (author + reviewer)
- [ ] All architectural guarantee tests pass
- [ ] Permission-gated agent spawning
- [ ] Context assembly through `ContextManager` only

---

## Phase 8: Knowledge Federation

**Status:** FUTURE

**Priority:** MEDIUM  
**Estimated Effort:** 6-8 weeks  
**Dependencies:** Phase 6 (External Bridge), Phase 7 (Multi-Agent)

### 8.1 Vector Search Constitutional Amendment

**Required:** No vector DB / embeddings without constitutional amendment

**Amendment process:**
1. Submit `governance/amendment_template.md`
2. UCGS profile update for vector capability
3. Constitutional pre-flight review
4. ratification vote

### 8.2 Knowledge Graph UI

**Deliverables:**
- [ ] Graph visualization for memory nodes/edges
- [ ] Query interface for memory lookup
- [ ] Cross-source knowledge federation (Obsidian + external)

### 8.3 Cross-Platform Search

**Deliverables:**
- [ ] Unified search across entities, notes, memory
- [ ] Filter by entity type, date, workspace
- [ ] Search result ranking by relevance

---

## Phase 9: Cross-Platform Expansion

**Status:** FUTURE

**Priority:** MEDIUM  
**Estimated Effort:** 8-12 weeks  
**Dependencies:** Phase 5 (Async), Phase 6 (External Bridge)

### 9.1 macOS Support

**Deliverables:**
- [ ] `platform/hotkey_provider_macos.py` (CGEvent tap)
- [ ] Accessibility permissions check and user prompt
- [ ] System tray parity with Windows

### 9.2 Linux Support

**Deliverables:**
- [ ] X11/Wayland hotkey detection
- [ ] System tray integration (libappindicator)
- [ ] Path handling for Linux filesystem

### 9.3 Platform Abstraction

**Deliverables:**
- [ ] Unified `PlatformService` abstraction
- [ ] Platform-specific overrides via config
- [ ] Cross-platform test automation

---

## Implementation Order

```
Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9
   ↑         ↑         ↑         ↑         ↑
   │         │         │         │         │
   Priority: Async   External   Multi-   Knowledge  Linux/
             perf    bridge     agent    graph    macOS
```

**Rationale:**
1. **Phase 5** (Async) — Infrastructure for all subsequent phases
2. **Phase 6** (External Bridge) — Unblocks MCP and external providers
3. **Phase 7** (Multi-Agent) — Requires Phase 5 infrastructure
4. **Phase 8** (Knowledge) — Requires Phase 6 external bridge
5. **Phase 9** (Platform) — Independent but benefits from Phase 5

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
| 5 — Async EventBus | 2-3 | HIGH | HIGH |
| 6 — External Bridge | 2-3 | MEDIUM | HIGH |
| 7 — Multi-Agent | 4-6 | HIGH | MEDIUM |
| 8 — Knowledge | 6-8 | MEDIUM | MEDIUM |
| 9 — Cross-Platform | 8-12 | MEDIUM | LOW |

**Total remaining:** 22-32 weeks (one developer)

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Async EventBus | 95th percentile dispatch latency < 50ms |
| External Bridge | MCP manifests load, capability catalog aggregates |
| Multi-Agent | Constitutional gate sign-off, permission-gated |
| Knowledge | Graph visualization, cross-source search |
| Cross-Platform | macOS + Linux hotkey + tray parity |
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
| `docs/architecture/VNEXT_STATE_DRIVEN_BLUEPRINT.md` | Cognitive stack (Program 5) |
| `docs/architecture/WORKSPACE_VISION.md` | Product north star |
| `docs/architecture/ASYNC_EVENTBUS_POLICY.md` | Phase 5 design |
| `docs/architecture/AGENT_RUNTIME_INTERFACE.md` | Phase 7 design |
| `docs/architecture/PROGRAM_3_WORKSPACE_ADOPTION.md` | Phase 2 reference |
| `docs/architecture/PLATFORM_STRATEGY.md` | Phase 9 design |

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
