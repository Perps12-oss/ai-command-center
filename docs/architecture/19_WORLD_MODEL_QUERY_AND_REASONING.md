# 19 — World Model Query and Reasoning

**Status:** Proposed (Planner Architecture — Document 19)  
**Authority:** Subordinate to `PROJECT_CONSTITUTION_V4.md` and `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Relation to other docs:** Builds on Layer 2 (World Model) in `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Constitutional constraint:** Planner = Reasoning; Runtime = Execution; World Model = Truth

---

## Purpose

This document defines how the planner answers:

```text
What should I retrieve from the graph?
```

before it can plan.

It is the missing piece that turns the World Model from storage into a reasoning substrate.

---

## The Problem

The World Model currently stores:

```text
Entities
Relationships
Timeline Events
```

But the planner needs to **query** and **reason about** this data, not just retrieve it.

Without query reasoning:

```text
Planner: "I need context about the project"
World Model: "Here are 10,000 entities"
Planner: "..."
```

With query reasoning:

```text
Planner: "I need context about the project"
Query Engine: "What type of context?"
Planner: "Files modified in the last week that relate to the current goal"
Query Engine: "Found 23 relevant entities with 156 relationships"
Planner: "Good. Summarize the top 5."
```

---

## Core Concepts

### Query Graph

The Query Graph is the planner's interface to the World Model.

```text
Planner → QueryGraph → World Model
```

### Relationship Traversal

The planner must be able to traverse relationships:

```text
Start Entity
↓
Follow Relationship Type
↓
Reach Target Entities
↓
Follow Next Relationship
↓
...
```

Example:

```text
Start: User's current project
Follow: CONTAINS
Reach: All tasks in project
Follow: ASSIGNED_TO
Reach: All team members
Follow: OWNS
Reach: All files owned by team members
```

### Context Expansion

Given a seed entity, expand to relevant context:

```text
Seed: task "Implement login"
↓
Expand: DERIVES_FROM → design doc
Expand: BLOCKS → integration test
Expand: REFERENCES → auth service
↓
Context Set: { login task, auth design, integration test, auth service }
```

### Relevance Ranking

Not all context is equal. Rank by:

```text
Recency          → Recently modified entities
Relevance        → Direct relationship to goal
Connectivity     → High-degree nodes may be hubs
Novelty          → New information vs. already-known
Actionability    → Entities that can be acted upon
```

### Subgraph Extraction

Extract focused subgraphs for planning:

```text
Full World Graph
↓
Query: "All entities within 2 hops of current goal"
↓
Subgraph: 47 entities, 312 relationships
↓
Planner Context
```

---

## Query Types

### Structural Queries

```text
"What entities are of type X?"
"What entities have attribute Y?"
"How many relationships of type Z exist?"
```

### Relationship Queries

```text
"What entities are related to X?"
"What entities are N hops away from X?"
"What paths exist between X and Y?"
```

### Temporal Queries

```text
"What changed since timestamp T?"
"What entities were created/modified in date range D?"
"What is the most recent entity of type X?"
```

### Goal-Oriented Queries

```text
"What entities are relevant to goal G?"
"What entities are blocked by entity X?"
"What entities depend on entity X?"
```

---

## Query Planning

The planner must plan its own queries:

```text
Goal: Refactor authentication module
↓
Sub-goal: Identify all auth-related files
Query 1: Find all entities with type FILE where name contains "auth"
↓
Sub-goal: Identify who owns these files
Query 2: For each file, find OWNER relationship
↓
Sub-goal: Find related tests
Query 3: For each auth file, find REFERENCES relationships to TEST entities
↓
Context Assembled
```

### Query Dependency Graph

```text
Query 1 (file discovery)
    ↓
Query 2 (owner lookup) ← Query 1 results
    ↓
Query 3 (test discovery) ← Query 1 results
    ↓
Query 4 (dependency analysis) ← Query 2 + Query 3 results
```

---

## Integration with Context Builder

Query reasoning feeds into Context & Memory Externalization (Document 11):

```text
Planner Goal
↓
Query Graph
↓
Relevant Entities (ranked)
↓
Context Builder
↓
Compression Tier Assignment
↓
Planner Context
```

### Feedback Loop

```text
Planner: "I have gaps in my context"
↓
Query Graph: "What specific information do you need?"
↓
Planner: "I need to understand the data flow"
↓
Query Graph: "Executing: Trace REFERENCED_BY relationships from data source"
↓
Planner: "Good. Now I can plan."
```

---

## Search Constraints

To prevent runaway queries:

```text
Max Query Depth = 5 hops
Max Entities Returned = 500
Max Query Time = 2 seconds
Max Queries Per Planning Session = 20
```

---

## EventBus Topics

```text
world.query.request          → Execute query against World Model
world.query.result          → Return query results
world.subgraph.request      → Extract subgraph
world.subgraph.result       → Return subgraph
world.relevance.rank        → Rank entities by relevance
world.relevance.scored      → Return scored entities
context.gap.detected       → Planner signals context gap
context.gap.filled          → Query fills the gap
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
| 10 | State Projection & Simulation | — |
| 11 | Context & Memory Externalization | — |
| 12 | Planning Budget System | — |
| 13 | Uncertainty & Missing Information | — |
| 14 | Human Collaboration Model | — |
| 15 | Goal Arbitration | — |
| 16 | Explainability Specification | — |
| 17 | Planner Constitutional Rules | — |
| 18 | Intelligence Benchmarks & Success Metrics | — |
| **19** | **World Model Query and Reasoning** | **This document** |

---

## References

| Document | Role |
|----------|------|
| `PROJECT_CONSTITUTION_V4.md` | Supreme authority |
| `VNEXT_STATE_DRIVEN_BLUEPRINT.md` | Cognitive stack architecture (L2 World Model) |
| `10_STATE_PROJECTION_AND_SIMULATION.md` | State projection requires good queries |
| `11_CONTEXT_AND_MEMORY_EXTERNALIZATION.md` | Query results feed context builder |
| `ADR-005_WORLD_MODEL_AUTHORITY.md` | World Model ownership rules |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-10 | Initial draft — World Model Query and Reasoning |
