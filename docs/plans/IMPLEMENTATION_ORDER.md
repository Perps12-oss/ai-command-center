# Implementation Order Recommendation

**Status:** RECOMMENDATION  
**Authority:** `MASTER_ROADMAP_2026.md`  
**Purpose:** Optimal phase implementation order based on dependencies

---

## Executive Summary

Based on dependency analysis, here's the recommended implementation order:

```
Phase 5-6 → Phase 8 → Phase 9 → Phase 10 → Phase 11
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
Complete  Operator   Goals &    World     Cross-
(Infra)    Kernel    Multi-    Model    Platform
           (Model   Agent    (Entity   (Platform
            Indep)   Coord)   Graph)   specific)
```

**Key insight:** Phase 8 (Operator Kernel) unblocks everything else. Complete Phase 5/6, then focus on Operator Kernel.

---

## Dependency Analysis

### Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DEPENDENCY RELATIONSHIPS                          │
└─────────────────────────────────────────────────────────────────────┘

Phase 5 (Async EventBus)
   │
   ├──► Phase 8 (Operator Kernel)  [REQUIRED]
   │        │
   │        └──► Phase 9 (Goals & Multi-Agent)  [REQUIRED]
   │                    │
   │                    └──► Phase 10 (World Model)  [REQUIRED]
   │
   └──► Phase 6 (External Bridge)  [COMPLETE]

Phase 6 (External Bridge)
   │
   └──► Phase 9 (Goals & Multi-Agent)  [BENEFITS]

Phase 8 (Operator Kernel) ← CRITICAL PATH
   │
   └──► Phase 9 (Goals & Multi-Agent)  [REQUIRED]

Phase 9 (Goals & Multi-Agent)
   │
   └──► Phase 10 (World Model)  [REQUIRED]

Phase 11 (Cross-Platform)
   │
   └──► Independent - Can overlap with any phase
```

---

## Recommended Order

### Sprint 0: Complete In-Progress (4-6 weeks)

```
┌─────────────────────────────────────────────────────────────┐
│ SPRINT 0: Complete Phase 5 & 6                            │
├─────────────────────────────────────────────────────────────┤
│ Phase 5: Async EventBus                                    │
│   • TieredDispatchPolicy                                   │
│   • Worker pools for R4b/R4c/R4d                          │
│   • Backward compatibility                                 │
│   Exit: 95th percentile < 50ms latency                    │
├─────────────────────────────────────────────────────────────┤
│ Phase 6: External Capability Bridge                         │
│   • MCP manifest schema                                    │
│   • Capability aggregation                                 │
│   • External provider integration                          │
│   Exit: MCP manifests load, catalog aggregates             │
└─────────────────────────────────────────────────────────────┘
```

**Why first?** Foundation work. No point building on unstable infrastructure.

---

### Sprint 1: Operator Kernel (6-8 weeks) — CRITICAL PATH

```
┌─────────────────────────────────────────────────────────────┐
│ SPRINT 1: Phase 8 - Operator Kernel                        │
├─────────────────────────────────────────────────────────────┤
│ Week 1-2: Core Kernel                                      │
│   • OperatorKernel base class                              │
│   • IntentResolver                                        │
│   • ModeResolver                                          │
├─────────────────────────────────────────────────────────────┤
│ Week 3-4: Model Adapter Layer                             │
│   • ModelAdapter contract                                 │
│   • Ollama adapter (existing)                            │
│   • OpenAI adapter                                       │
│   • Anthropic adapter                                    │
├─────────────────────────────────────────────────────────────┤
│ Week 5-6: Compliance Engine                               │
│   • Hallucination detection                              │
│   • Contract validation                                   │
│   • Response contracts                                    │
├─────────────────────────────────────────────────────────────┤
│ Week 7-8: Integration & Testing                           │
│   • PromptAssemblyService                                 │
│   • Golden test suite                                     │
│   • Model independence verification                       │
└─────────────────────────────────────────────────────────────┘

EXIT CRITERIA:
✓ Model independence score > 0.95
✓ Compliance catches 100% test hallucinations
✓ Same behavior across all model adapters
```

**Why critical?** Everything else depends on consistent operator behavior.

---

### Sprint 2: Goals & Multi-Agent (8-10 weeks)

```
┌─────────────────────────────────────────────────────────────┐
│ SPRINT 2: Phase 9 - Goals & Multi-Agent                   │
├─────────────────────────────────────────────────────────────┤
│ Week 1-2: Goal Engine                                     │
│   • Goal entity & repository                              │
│   • Goal lifecycle management                             │
│   • SQLite persistence                                    │
├─────────────────────────────────────────────────────────────┤
│ Week 3-4: Planning Engine                                 │
│   • Planning pipeline (Explore→Plan→Validate→Execute)    │
│   • TaskGraph DAG structure                               │
│   • ExecutionPlan generation                              │
├─────────────────────────────────────────────────────────────┤
│ Week 5-6: Agent Framework                                │
│   • AgentContract declarations                            │
│   • AgentCoordinator service                              │
│   • PolicyEngine (permissions)                            │
├─────────────────────────────────────────────────────────────┤
│ Week 7-8: Agent Lifecycle                                 │
│   • Agent spawn/terminate                                │
│   • Task assignment                                      │
│   • Timeline audit trail                                  │
├─────────────────────────────────────────────────────────────┤
│ Week 9-10: Integration & Testing                           │
│   • Multi-agent collaboration                             │
│   • Constitutional gate sign-off                          │
│   • Operator approval flows                               │
└─────────────────────────────────────────────────────────────┘

EXIT CRITERIA:
✓ Goals persist across restarts
✓ Multiple agents can collaborate
✓ Operator approval required for high-risk
✓ Constitutional gate signed off
```

**Note:** Benefits from Phase 6 capability catalog for agent capabilities.

---

### Sprint 3: World Model (10-12 weeks)

```
┌─────────────────────────────────────────────────────────────┐
│ SPRINT 3: Phase 10 - World Model                          │
├─────────────────────────────────────────────────────────────┤
│ Week 1-3: Core World Model                                 │
│   • WorldModelService                                     │
│   • Entity & EntityType                                   │
│   • EntityGraph structure                                 │
│   • Relationship engine                                   │
├─────────────────────────────────────────────────────────────┤
│ Week 4-6: Context Engine                                  │
│   • EntityContext assembly                               │
│   • State projections (Workspace, Goal, Project)          │
│   • Context from entities (not conversation)             │
├─────────────────────────────────────────────────────────────┤
│ Week 7-9: Advanced Features                               │
│   • Predictive operations                                 │
│   • Undo/Replay framework                                │
│   • Cross-workspace intelligence                         │
├─────────────────────────────────────────────────────────────┤
│ Week 10-12: UI & Integration                             │
│   • World Explorer view                                  │
│   • Relationship visualizer                              │
│   • Full integration testing                              │
└─────────────────────────────────────────────────────────────┘

EXIT CRITERIA:
✓ ACC reasons from entities, not conversation
✓ World Explorer functional
✓ Predictive operations identify blockers
✓ Undo/Replay operational
```

---

### Sprint 4+: Cross-Platform (8-12 weeks, can overlap)

```
┌─────────────────────────────────────────────────────────────┐
│ SPRINT 4: Phase 11 - Cross-Platform                      │
├─────────────────────────────────────────────────────────────┤
│ Can run parallel to any Sprint after Phase 5 complete     │
│ No hard dependencies on other features                    │
├─────────────────────────────────────────────────────────────┤
│ Week 1-4: macOS                                          │
│   • CGEvent hotkey provider                              │
│   • NSStatusItem tray                                    │
│   • Permissions handling                                 │
├─────────────────────────────────────────────────────────────┤
│ Week 5-8: Linux                                          │
│   • X11 hotkey provider                                 │
│   • AppIndicator tray                                    │
│   • Wayland fallback                                     │
├─────────────────────────────────────────────────────────────┤
│ Week 9-12: Platform Abstraction                           │
│   • PlatformService ABC                                  │
│   • Unified configuration                                │
│   • Cross-platform testing                               │
└─────────────────────────────────────────────────────────────┘

EXIT CRITERIA:
✓ macOS hotkey & tray working
✓ Linux hotkey & tray working
✓ Platform abstraction stable
```

---

## Timeline Summary

```
Year 1
────────────────────────────────────────────────────────────────────
Q3 2026
├── Sprint 0 (Complete Phase 5-6):      ████████  4-6 weeks
│
├── Sprint 1 (Operator Kernel):          ████████████████  6-8 weeks
│
└── Sprint 2 Start (Goals):               ████

Q4 2026
├── Sprint 2 (Goals & Multi-Agent):      ██████████████████  8-10 weeks
│
├── Sprint 3 Start (World Model):        ████
│
└── Sprint 4 Start (Cross-Platform):     ████  (parallel)

Q1 2027
├── Sprint 3 (World Model):              ████████████████████  10-12 weeks
│
└── Sprint 4 Continue (Cross-Platform): ████████  (parallel)

Q2 2027
├── Sprint 4 Complete (Cross-Platform): ██████  8-12 weeks total
│
└── Phase 11 Exit:                       ✓
```

**Total: ~40-52 weeks (8-10 months)**

---

## Parallelization Opportunities

### Can Run in Parallel

| Combination | Why |
|-------------|-----|
| Phase 6 + Phase 8 | External Bridge provides capabilities for agents, Operator Kernel provides behavior |
| Phase 11 + Any | Platform work is independent |
| Sprint 4 (Platform) + Sprint 3 (World Model) | Different teams, no dependencies |

### Critical Path

```
Phase 5 → Phase 8 → Phase 9 → Phase 10
   │          │          │          │
   └──(6)─────┘          │          │
                         │          │
                    (11 parallel)   │
                                   │
                              (11 parallel)
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Phase 8 (Operator Kernel) takes longer than expected | Phase 9 can start with partial kernel (just Intent/Mode resolver) |
| Model adapter complexity | Start with Ollama (existing), then add OpenAI/Claude |
| Agent coordination complexity | Start with single-agent goals, add multi-agent later |
| World Model performance | Start with simple projections, add predictive later |

---

## Decision Points

### Should we do Phase 6 before Phase 8?

**Answer: Phase 6 can be parallel with Sprint 1**

- Phase 6 (External Bridge) provides MCP capabilities
- Phase 8 (Operator Kernel) provides behavior
- They don't block each other
- Both complete before Phase 9

### Should we start Cross-Platform early?

**Answer: Yes, after Phase 5**

- Platform work is independent
- Can run parallel
- No waiting for features
- Early feedback on platform support

### Can we ship Phase 8 before Phase 9?

**Answer: Yes**

- Phase 8 is valuable standalone
- Operator Kernel works without Goals
- Users get model independence
- Phase 9 adds goal management

---

## Recommended Starting Point

```
IMMEDIATE: Complete Phase 5 (Async EventBus)
   └── Required for all subsequent work

NEXT:     Start Phase 8 (Operator Kernel)
   └── Critical path starts here

PARALLEL: Start Phase 11 (Cross-Platform)
   └── Independent, good early feedback

AFTER 8: Start Phase 9 (Goals & Multi-Agent)
   └── Requires Operator Kernel

AFTER 9: Start Phase 10 (World Model)
   └── Requires Goals as entities
```

---

## Summary

| Priority | Phase | Duration | Dependencies |
|----------|-------|----------|--------------|
| 1 | Phase 5 (Async) | 2-3 weeks | None |
| 2 | Phase 8 (Operator Kernel) | 6-8 weeks | Phase 5 |
| 3 | Phase 9 (Goals) | 8-10 weeks | Phase 8 |
| 4 | Phase 10 (World Model) | 10-12 weeks | Phase 9 |
| Parallel | Phase 6 (External Bridge) | 2-3 weeks | None |
| Parallel | Phase 11 (Cross-Platform) | 8-12 weeks | Phase 5 |

**Critical path:** Phase 5 → Phase 8 → Phase 9 → Phase 10  
**Total:** 26-33 weeks primary + parallel work

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial recommendation |
