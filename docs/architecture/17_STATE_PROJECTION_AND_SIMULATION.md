# 10 — State Projection & Simulation

**Status:** Proposed (Planner Architecture — Document 10)  
**Authority:** Subordinate to `PROJECT_CONSTITUTION_V4.md` and `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Relation to other docs:** Builds on Layer 4 (Planner) in `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Constitutional constraint:** Planner = Reasoning; Runtime = Execution; World Model = Truth

---

## Purpose

This document defines the simulation layer that allows the planner to evaluate candidate plans without touching reality.

The planner's biggest weakness is:

```text
Current State
↓
Guess
↓
Action
```

The planner should evolve to:

```text
Current State
↓
Project Future State
↓
Evaluate Outcome
↓
Select Plan
```

---

## Why Not "Speculative Execution"?

"Speculative execution" leads engineers toward building a miniature autonomous agent runtime inside the planner. That's how projects accidentally end up with:

```text
Planner
→ Planner Runtime
→ Planner Executor
→ Planner Sandbox
→ Planner Agent
→ Actual Runtime
```

which duplicates half the ACC Brain.

**State Projection & Simulation** preserves the constitutional separation:

```text
Planner = Reasoning
Runtime = Execution
World Model = Truth
```

---

## Required Concepts

### State Projection

Define:

```text
ProjectedState = Simulate(
    CurrentState,
    CandidateAction
)
```

The planner must be able to estimate:

```text
Before:
Downloads = 500 files

Candidate Action:
Archive Screenshots

Projected State:
Downloads = 300 files
```

without touching reality.

---

## Simulation Rules

The simulation layer:

**MAY:**

```text
Read WorldState
Clone WorldState
Apply Simulated Mutations
Generate Projected States
```

**MAY NOT:**

```text
Write WorldModel
Call Capabilities
Execute Runtime Actions
Modify Real Files
```

---

## Branch Exploration

Define:

```text
Candidate Plan A
Candidate Plan B
Candidate Plan C
```

and compare outcomes.

The Deep Planner should be capable of:

```text
Current State
↓
Generate Alternatives
↓
Project Outcomes
↓
Evaluate Outcomes
↓
Select Best Candidate
```

---

## Search Constraints

Do NOT permit unrestricted tree expansion.

Specify:

```text
Max Branches
Max Depth
Max Simulation Time
Max Planner Cost
```

Example:

```text
Max Branches = 5
Max Depth = 3
Max Simulation Budget = 2 seconds
```

---

## Rollback Rules

Projected states must be disposable.

Simulation output:

```text
Current State
→ Clone
→ Simulate
→ Evaluate
→ Destroy Clone
```

No projected state may survive beyond evaluation.

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
| **17** | **State Projection & Simulation** | **This document** |
| 18 | Context & Memory Externalization | — |
| 19 | World Model Query and Reasoning | — |

---

## References

| Document | Role |
|----------|------|
| `PROJECT_CONSTITUTION_V4.md` | Supreme authority |
| `VNEXT_STATE_DRIVEN_BLUEPRINT.md` | Cognitive stack architecture |
| `ADR-005_WORLD_MODEL_AUTHORITY.md` | World Model ownership rules |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-10 | Initial draft — State Projection & Simulation |
