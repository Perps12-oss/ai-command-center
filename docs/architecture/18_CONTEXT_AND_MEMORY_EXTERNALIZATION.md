# 11 — Context & Memory Externalization

**Status:** Proposed (Planner Architecture — Document 11)  
**Authority:** Subordinate to `PROJECT_CONSTITUTION_V4.md` and `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Relation to other docs:** Builds on Layer 1 (Memory) and Layer 2 (World Model) in `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Constitutional constraint:** Planner = Reasoning; Runtime = Execution; World Model = Truth

---

## Purpose

This document determines whether ACC remains useful after six months.

Without it:

```text
Workspace grows
↓
Prompt grows
↓
Planner dies
```

Context & Memory Externalization is the mechanism that keeps the planner alive as the workspace scales.

---

## Memory Layers

### Working Memory

Current planning session only.

Contains:

```text
Current Goal
Current State
Active Constraints
Current Plan
```

**Lifetime:** Planning session only  
**Storage:** In-memory structures  
**Cleared:** After plan execution or abandonment

---

### Episodic Memory

Historical experiences.

Contains:

```text
Successful Plans
Failed Plans
Reflections
Past Outcomes
```

**Lifetime:** Persistent  
**Storage:** Memory Graph (`memory_nodes`, `memory_edges`)  
**Retrieval:** By goal similarity, time range, or outcome type

---

### Semantic Memory

Long-lived knowledge.

Contains:

```text
Workspace Structure
Project Relationships
User Preferences
Capability Knowledge
```

**Lifetime:** Persistent  
**Storage:** World Model (entities, relationships)  
**Retrieval:** By entity type, relationship path, or attribute

---

## Context Paging Protocol

The planner must never receive the entire workspace.

The Context Builder must decide:

```text
What stays
What gets summarized
What gets removed
What gets fetched later
```

### Decision Framework

| Factor | Action |
|--------|--------|
| High relevance to current goal | Include |
| Recently modified | Include with recency marker |
| Medium relevance | Summarize |
| Low relevance | Reference only |
| No relevance | Exclude |

---

## Retrieval Rules

Example:

```text
Need:
launch_layout.json

Load:
File metadata
Folder relationships

Do not load:
Entire repository contents
```

### Metadata-First Pattern

Always load:

```text
Entity metadata (type, name, id, last_modified)
Relationship summary (counts, types, connections)
```

Only load full content when:

```text
Entity is directly implicated in current goal
Entity is a focus entity (user explicitly mentioned)
Entity is a high-value context carrier (e.g., config files)
```

---

## Compression Strategy

Support tiered compression:

```text
Raw Data
↓
Summary
↓
Metadata
↓
Reference Only
```

### Tier Definitions

| Tier | Content | Token Estimate |
|------|---------|---------------|
| Raw | Full file contents | 100% |
| Summary | LLM-generated abstract | 10-20% |
| Metadata | Type, size, relationships | 1-5% |
| Reference | Entity ID and type only | <1% |

### Scaling Targets

This is how ACC eventually scales to:

```text
Thousands of files
Thousands of notes
Years of history
```

without exceeding context limits.

---

## Context Budget Management

The Context Builder must enforce a maximum context budget:

```text
Max Context Tokens = 32,000 (example)
Current Usage = 0
Remaining = 32,000
```

### Budget Allocation

| Component | Allocation |
|-----------|------------|
| Current goal | 500 tokens |
| Working memory | 2,000 tokens |
| Episodic memory (summarized) | 5,000 tokens |
| Semantic memory (entities) | 20,000 tokens |
| Capability catalog | 3,000 tokens |
| Scratch space | 1,500 tokens |

---

## EventBus Topics

The Context Builder publishes and subscribes to:

```text
context.build_request     → Start context assembly
context.build_progress    → Report tier completion
context.build_complete    → Deliver assembled context
context.evict_request     → Request tier downgrade
context.evicted           → Confirm tier downgrade
memory.lookup_request     → Fetch episodic memories
memory.lookup_result      → Deliver episodic memories
workspace.context.request → Fetch semantic memories
workspace.context.result  → Deliver semantic memories
```

---

## Integration with Planner Architecture

This document is part of the Planner Architecture specification:

| # | Document | Status |
|---|----------|--------|
| 01 | Planner Architecture | — |
| 02 | World State Model | — |
| 03 | Plan Graph Specification | — |
| 04 | Constraint Engine | — |
| 05 | Plan Evaluation Framework | — |
| 06 | Goal Decomposition Engine | — |
| 07 | Reflection Engine | — |
| 08 | Planner Memory | — |
| 09 | Model Routing | — |
| 10 | Planning Budget System | — |
| 11 | Uncertainty & Missing Information | — |
| 12 | Human Collaboration Model | — |
| 13 | Goal Arbitration | — |
| 14 | Explainability Specification | — |
| 15 | Planner Constitutional Rules | — |
| 16 | Success Metrics & Intelligence Benchmarks | — |
| 17 | State Projection & Simulation | — |
| **18** | **Context & Memory Externalization** | **This document** |
| 19 | World Model Query and Reasoning | — |

---

## References

| Document | Role |
|----------|------|
| `PROJECT_CONSTITUTION_V4.md` | Supreme authority |
| `VNEXT_STATE_DRIVEN_BLUEPRINT.md` | Cognitive stack architecture (L1 Memory, L2 World Model) |
| `PERSISTENCE_ABSTRACTION.md` | Brain Phase 0 — World Model repository interface |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-10 | Initial draft — Context & Memory Externalization |
