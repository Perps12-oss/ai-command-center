# 13 — Goal Arbitration

**Status:** Proposed (Planner Architecture — Document 13)  
**Authority:** Subordinate to `PROJECT_CONSTITUTION_V4.md` and `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Relation to other docs:** Multi-goal coordination for Planner (Layer 4)  
**Constitutional constraint:** Planner = Reasoning; Runtime = Execution; World Model = Truth

---

## Purpose

Today:

```text
One Goal
```

Tomorrow:

```text
Organize Downloads
Reply to Email
Update Obsidian Notes
Schedule Meeting
```

All at once.

You have a Scheduler. You do NOT have Goal Arbitration.

Goal Arbitration determines **who wins** when goals conflict.

---

## The Problem

When multiple goals exist:

```text
Goal A: Organize Downloads
Goal B: Reply to Email
Goal C: Update Obsidian Notes
Goal D: Schedule Meeting
```

Questions arise:

```text
Which goal should execute first?
Which goals can run in parallel?
Which goals block which goals?
What if two goals need the same resource?
What if two goals have conflicting effects?
```

The Scheduler handles **when** goals run. Goal Arbitration handles **which** goals run and **how** conflicts resolve.

---

## Goal Properties

### Priority

Static importance level assigned by user or system.

```text
Critical > High > Normal > Low > Background
```

### Urgency

Time-sensitive importance.

```text
Now > Soon > Eventually > When-idle
```

### Impact

Expected outcome magnitude.

```text
High Impact: Major project milestone, system-wide change
Medium Impact: Feature delivery, significant refactor
Low Impact: Cleanup, minor improvement
```

### Dependencies

Goal relationships.

```text
depends_on: Goal A must complete before Goal B
blocks: Goal A blocks Goal B
conflicts_with: Goal A and Goal B cannot coexist
enhances: Completing Goal A improves Goal B outcome
```

### Resource Cost

Resources required for goal completion.

```text
CPU: 0-100%
Memory: 0-N GB
Network: yes/no
External Services: yes/no
Human Attention: yes/no
```

---

## Arbitration Dimensions

### Temporal Priority

Which goal is more urgent?

```text
Goal A: "Fix critical bug" (deadline: 1 hour)
Goal B: "Refactor module" (deadline: 1 week)

Winner: Goal A (temporal priority)
```

### Impact Priority

Which goal has greater impact?

```text
Goal A: "Update documentation" (low impact)
Goal B: "Fix authentication" (high impact)

Winner: Goal B (impact priority)
```

### Dependency Priority

Which goal unblocks more work?

```text
Goal A: "Update docs" (no dependents)
Goal B: "Fix API contract" (unblocks 5 other goals)

Winner: Goal B (dependency priority)
```

### Resource Priority

Which goal has better resource efficiency?

```text
Goal A: "Generate 100 reports" (high CPU)
Goal B: "Send batch emails" (low CPU, network only)

Winner: Depends on current resource availability
```

---

## Conflict Resolution Strategies

### FIFO (First In, First Out)

Oldest goal wins.

```text
When: Equal priority, no dependencies
Pros: Simple, predictable
Cons: May miss urgent items
```

### LIFO (Last In, First Out)

Newest goal wins.

```text
When: Newer goals are more urgent
Pros: Prioritizes recent context
Cons: Older important goals may starve
```

### Priority-First

Highest priority wins.

```text
When: Clear priority levels
Pros: Aligns with user intent
Cons: Low-priority items may never run
```

### Deadline-First

Most urgent deadline wins.

```text
When: Time-sensitive goals exist
Pros: Never misses deadlines
Cons: May deprioritize important non-urgent work
```

### Impact-First

Highest impact wins.

```text
When: Maximizing value is priority
Pros: Optimizes outcomes
Cons: Small wins never happen
```

### Dependency-First

Goal that unblocks most others wins.

```text
When: Complex dependency graph exists
Pros: Maximizes throughput
Cons: May delay isolated goals
```

---

## Conflict Types

### Resource Contention

Two goals need the same exclusive resource.

```text
Goal A: "Rebuild database schema"
Goal B: "Run production queries"

Resolution: Dependency-based ordering or human decision
```

### Effect Conflict

Two goals have contradictory effects.

```text
Goal A: "Delete temp files"
Goal B: "Restore temp files from backup"

Resolution: Dependency-based ordering or human decision
```

### State Conflict

Two goals require different system states.

```text
Goal A: "Enable maintenance mode"
Goal B: "Process user requests"

Resolution: Explicit state transitions required
```

### Priority Conflict

Equal priority goals block each other.

```text
Goal A: "Fix bug #123" (priority: high)
Goal B: "Fix bug #456" (priority: high)

Resolution: Urgency or impact tiebreaker
```

---

## Arbitration Algorithm

```
Input: Set of pending goals G
Output: Ordered goal queue Q

1. Score each goal in G
   score = (priority_weight × priority) +
           (urgency_weight × urgency) +
           (impact_weight × impact) +
           (dependency_weight × unblocks_count) +
           (resource_efficiency × 1/cost)

2. Identify conflicts
   for each pair (g1, g2) in G:
       if conflicts(g1, g2):
           mark conflict, determine type

3. Resolve conflicts
   for each conflict:
       if type == resource_contention:
           apply resource priority
       elif type == effect_conflict:
           apply dependency priority or escalate
       elif type == state_conflict:
           escalate to human
       else:
           use highest score

4. Generate ordered queue
   Q = sort(G, by=score, descending)

5. Insert dependency constraints
   Q = respect_dependencies(Q)

6. Return Q
```

---

## Weight Configuration

```yaml
arbitration:
  weights:
    priority: 0.3
    urgency: 0.25
    impact: 0.25
    dependency: 0.1
    resource_efficiency: 0.1
  
  conflict_resolution:
    resource_contention: dependency_first
    effect_conflict: dependency_first
    state_conflict: escalate
    priority_conflict: urgency_tiebreaker
```

---

## Escalation

When arbitration cannot resolve:

```text
Conflict Detected
↓
Try automated resolution
↓
If unresolved:
    → Flag for human decision
    → Show both goals, both plans
    → Human picks winner
```

---

## EventBus Topics

```text
goals.arbitration.request     → Multiple goals need ordering
goals.arbitration.scored     → Goals scored by arbitration
goals.arbitration.conflict   → Conflict detected
goals.arbitration.resolved   → Conflict resolved
goals.arbitration.escalated  → Human decision required
goals.arbitration.ordered    → Final queue produced
```

---

## Integration with Scheduler

The Scheduler receives ordered goals from Goal Arbitration:

```text
Scheduler → Request arbitration
Goal Arbitrator → Returns ordered queue
Scheduler → Executes in order
Goal Arbitrator → Re-arbitrates on new goal arrival
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
| 10 | Planning Budget System | — |
| 11 | Uncertainty & Missing Information | — |
| 12 | Human Collaboration Model | — |
| **13** | **Goal Arbitration** | **This document** |
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
| `SCHEDULER_ABSTRACTION.md` | Scheduler integration |
| `12_HUMAN_COLLABORATION_MODEL.md` | Escalation handling |
| `16_SUCCESS_METRICS_AND_INTELLIGENCE_BENCHMARKS.md` | Arbitration quality metrics |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-10 | Initial draft — Goal Arbitration |
