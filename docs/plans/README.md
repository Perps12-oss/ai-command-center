# Phase Plans Index

This directory contains detailed implementation plans for each phase of the AI Command Center roadmap.

---

## Master Roadmap

| Document | Description |
|----------|-------------|
| `../MASTER_ROADMAP_2026.md` | Consolidated 4-phase roadmap with all phases |

---

## Phase Plans

| Phase | Document | Status | Priority |
|-------|----------|--------|----------|
| 5 | `PHASE_5_ASYNC_EVENTBUS_PLAN.md` | IN PROGRESS | HIGH |
| 6 | `PHASE_6_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md` | IN PROGRESS | HIGH |
| 7 | `PHASE_7_MULTI_AGENT_RUNTIME_PLAN.md` | GATED | MEDIUM |
| 8 | `PHASE_8_KNOWLEDGE_FEDERATION_PLAN.md` | FUTURE | MEDIUM |
| 9 | `PHASE_9_CROSS_PLATFORM_PLAN.md` | FUTURE | LOW |

---

## Phase Dependencies

```
Phase 5 ──┬── Phase 6 ──┬── Phase 7 ──┬── Phase 8
          │             │             │
Async     External      Multi-       Knowledge
EventBus  Bridge        Agent        Federation
                          │
                          │
                          └── Phase 9
                              │
                          Cross-
                          Platform
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

### Gated

**Phase 7 — Multi-Agent Runtime**
- Requires constitutional gate sign-off
- All 3 constitutional questions must be answered
- See `PHASE_7_MULTI_AGENT_RUNTIME_PLAN.md`

### Future

**Phase 8 — Knowledge Federation**
- Requires constitutional amendment for vector search
- Cross-source unified search
- Graph visualization

**Phase 9 — Cross-Platform**
- macOS and Linux support
- Platform abstraction layer
- Platform-specific implementations

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
