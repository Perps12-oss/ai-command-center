# Phase Plans Index

This directory contains detailed implementation plans for each phase of the AI Command Center roadmap.

---

## Master Roadmap

| Document | Description |
|----------|-------------|
| `../MASTER_ROADMAP_2026.md` | Consolidated roadmap with all phases 1-11 |

---

## Key Reference

| Document | Description |
|----------|-------------|
| `PHASE_7_8_9_10_QA.md` | **CRITICAL** — 5 key questions and detailed answers about Phases 7-10 |

---

## Phase Plans

| Phase | Document | Status | Priority |
|-------|----------|--------|----------|
| 5 | `PHASE_5_ASYNC_EVENTBUS_PLAN.md` | IN PROGRESS | HIGH |
| 6 | `PHASE_6_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md` | IN PROGRESS | HIGH |
| 7 | `PHASE_7_MULTI_AGENT_RUNTIME_PLAN.md` | Superseded | — |
| **8** | `PHASE_8_OPERATOR_KERNEL_PLAN.md` | **PLANNED** | **HIGH** |
| **9** | `PHASE_9_GOALS_MULTI_AGENT_PLAN.md` | **PLANNED** | **HIGH** |
| **10** | `PHASE_10_WORLD_MODEL_PLAN.md` | **FUTURE** | **MEDIUM** |
| 11 | `PHASE_9_CROSS_PLATFORM_PLAN.md` | FUTURE | LOW |

---

## Phase Dependencies

```
Phase 7 ──► Phase 8 ──► Phase 9 ──► Phase 10
   │           │           │           │
   ▼           ▼           ▼           ▼
Operational  Operator   Goals &    World Model
Intelligence Kernel    Multi-Agent

Phase 5 ──► All phases (Async EventBus required)
```

---

## Quick Reference

### In Progress

**Phase 5 — Async EventBus**
- Implement non-blocking dispatch for heavy handlers
- Target: 95th percentile < 50ms latency
- Design: `ASYNC_EVENTBUS_POLICY.md`

**Phase 6 — External Capability Bridge**
- Aggregate MCP and external capabilities
- Integrate with planner capability catalog
- Design: `AGENT_RUNTIME_INTERFACE.md`

### Planned (Phases 8-10)

**Phase 8 — Operator Kernel & Model Independence**
- Model-agnostic operator platform
- Core: "Behavior belongs to ACC, Reasoning belongs to LLM"
- Key: `PHASE_8_OPERATOR_KERNEL_PLAN.md`

**Phase 9 — Goals & Multi-Agent Coordination**
- Goal-driven workspace OS
- Core: "Commands are temporary, Goals persist"
- Key: `PHASE_9_GOALS_MULTI_AGENT_PLAN.md`

**Phase 10 — World Model & Reasoning**
- Entity-driven reasoning
- Core: "ACC reasons from entities, not conversation"
- Key: `PHASE_10_WORLD_MODEL_PLAN.md`

### Future

**Phase 11 — Cross-Platform**
- macOS and Linux support
- Platform abstraction layer

---

## Contributing

When updating phase plans:

1. Update status in the phase document header
2. Update the index table
3. Update the master roadmap
4. Run verification gates before marking complete

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial index created |
