# 10 — Planning Budget System

**Status:** Proposed (Planner Architecture — Document 10)  
**Authority:** Subordinate to `PROJECT_CONSTITUTION_V4.md` and `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Relation to other docs:** Core constraint system for Planner (Layer 4)  
**Constitutional constraint:** Planner = Reasoning; Runtime = Execution; World Model = Truth

---

## Purpose

This document defines explicit limits that prevent the planner from thinking forever.

Without budget constraints, one day you'll discover:

```text
Goal
→ Replan
→ Reflect
→ Replan
→ Reflect
→ Replan
↓
Forever
```

Budget limits ensure the planner is predictable, cost-effective, and safe.

---

## Budget Dimensions

### Max Planning Iterations

```text
Maximum number of times the planner may loop before concluding.
```

| Goal Complexity | Max Iterations |
|-----------------|----------------|
| Simple | 1 |
| Moderate | 3 |
| Complex | 5 |
| Critical | 10 |

### Max Replan Attempts

```text
Maximum number of times the planner may regenerate a plan.
```

After this limit:

```text
→ Escalate to human review
→ Use cached solution
→ Abandon goal
```

### Max DAG Nodes

```text
Maximum number of nodes in the plan graph.
```

| Goal Complexity | Max Nodes |
|-----------------|-----------|
| Simple | 10 |
| Moderate | 25 |
| Complex | 50 |
| Critical | 100 |

### Max Context Tokens

```text
Maximum tokens allocated for context assembly.
```

| Priority | Budget |
|----------|--------|
| Background | 8,000 tokens |
| Normal | 16,000 tokens |
| High | 32,000 tokens |
| Critical | 64,000 tokens |

### Max Planner Cost

```text
Maximum cost (in compute or credits) per planning session.
```

Example:

```text
Simple Goal: $0.01
Moderate Goal: $0.05
Complex Goal: $0.25
Critical Goal: $1.00
```

### Max Planner Runtime

```text
Maximum wall-clock time for planning.
```

| Goal Complexity | Max Runtime |
|-----------------|-------------|
| Simple | 2 seconds |
| Moderate | 10 seconds |
| Complex | 30 seconds |
| Critical | 60 seconds |

### Max Reflection Cycles

```text
Maximum number of self-reflection loops.
```

After this limit:

```text
→ Commit to current plan
→ Flag for human review
→ Proceed with partial confidence
```

---

## Budget Escalation

When a budget is exhausted:

```text
Budget Exhausted
↓
Check escalation path
↓
If escalation configured:
    → Escalate (human review, cached solution, etc.)
↓
If no escalation:
    → Use current best plan
    → Flag uncertainty
```

### Escalation Paths

| Budget Type | Escalation Action |
|-------------|-------------------|
| Iterations | Use cached plan or escalate |
| Replans | Commit to current plan |
| Nodes | Simplify plan or split goal |
| Tokens | Reduce context or summarize |
| Cost | Throttle or abort |
| Runtime | Use heuristic plan |
| Reflection | Proceed with flagged uncertainty |

---

## Budget Tiers

### Tier 1 — Simple Goals

```text
One clear action
Known state
Low impact
```

Defaults:

```text
Max Iterations: 1
Max Replans: 0
Max Nodes: 10
Max Tokens: 8,000
Max Runtime: 2s
```

### Tier 2 — Moderate Goals

```text
Few actions
Mostly known state
Moderate impact
```

Defaults:

```text
Max Iterations: 3
Max Replans: 2
Max Nodes: 25
Max Tokens: 16,000
Max Runtime: 10s
```

### Tier 3 — Complex Goals

```text
Multiple actions
Partial state
High impact
```

Defaults:

```text
Max Iterations: 5
Max Replans: 3
Max Nodes: 50
Max Tokens: 32,000
Max Runtime: 30s
```

### Tier 4 — Critical Goals

```text
Many actions
Unknown state
Very high impact
```

Defaults:

```text
Max Iterations: 10
Max Replans: 5
Max Nodes: 100
Max Tokens: 64,000
Max Runtime: 60s
```

---

## Budget Monitoring

The planner must expose budget state:

```json
{
  "planning_session_id": "...",
  "tier": "complex",
  "budget": {
    "iterations": { "used": 2, "max": 5 },
    "replans": { "used": 1, "max": 3 },
    "nodes": { "used": 15, "max": 50 },
    "tokens": { "used": 12000, "max": 32000 },
    "runtime_ms": { "used": 8500, "max": 30000 },
    "reflection_cycles": { "used": 1, "max": 3 }
  },
  "remaining_budget_pct": 65,
  "should_escalate": false
}
```

---

## EventBus Topics

```text
planner.budget.initialized    → Budget tier assigned
planner.budget.consumed      → Budget updated
planner.budget.warning       → Budget threshold reached (80%)
planner.budget.exhausted     → Budget limit reached
planner.budget.escalated     → Escalation triggered
```

---

## Integration with Planner Architecture

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
| **10** | **Planning Budget System** | **This document** |
| 11 | Uncertainty & Missing Information | — |
| 12 | Human Collaboration Model | — |
| 13 | Goal Arbitration | — |
| 14 | Explainability Specification | — |
| 15 | Planner Constitutional Rules | — |
| 16 | Success Metrics & Intelligence Benchmarks | — |
| 17 | State Projection & Simulation | — |
| 18 | Context & Memory Externalization | — |
| 19 | World Model Query and Reasoning | — |

---

## References

| Document | Role |
|----------|------|
| `PROJECT_CONSTITUTION_V4.md` | Supreme authority |
| `VNEXT_STATE_DRIVEN_BLUEPRINT.md` | Cognitive stack architecture |
| `11_UNCERTAINTY_AND_MISSING_INFORMATION.md` | Escalation triggers |
| `16_SUCCESS_METRICS_AND_INTELLIGENCE_BENCHMARKS.md` | Budget optimization metrics |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-10 | Initial draft — Planning Budget System |
