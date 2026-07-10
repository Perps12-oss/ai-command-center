# 11 — Uncertainty & Missing Information

**Status:** Proposed (Planner Architecture — Document 11)  
**Authority:** Subordinate to `PROJECT_CONSTITUTION_V4.md` and `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Relation to other docs:** Core reasoning capability for Planner (Layer 4)  
**Constitutional constraint:** Planner = Reasoning; Runtime = Execution; World Model = Truth

---

## Purpose

Current planners assume:

```text
State is known
```

Reality:

```text
State is incomplete
```

Example:

```text
Move launch file
```

Planner doesn't know:

```text
Which launch file?
Which project?
Which directory?
```

A good planner must reason about uncertainty — not fabricate answers.

---

## Uncertainty Taxonomy

### Unknown State

The planner has no information about a required piece of state.

```text
Example: Which files exist in the project?
```

**Planner response:** Request information from World Model or human.

### Ambiguous State

Multiple interpretations exist and the planner cannot determine which is correct.

```text
Example: "launch" could mean:
- launch.json (VS Code)
- launch.sh (script)
- launch.py (module)
```

**Planner response:** Request clarification from human.

### Conflicting State

Available information contradicts itself.

```text
Example: File exists at path A, but references point to path B.
```

**Planner response:** Flag conflict, escalate, or request resolution.

### Stale State

Information exists but may be outdated.

```text
Example: Workspace model shows file at path, but filesystem may have changed.
```

**Planner response:** Request fresh state or proceed with uncertainty flag.

### Missing State

Required state is structurally absent.

```text
Example: Goal references "the config file" but no config entity exists.
```

**Planner response:** Request creation or clarification.

---

## Uncertainty Actions

When the planner encounters uncertainty, it has five options:

### ACT

Proceed with best guess based on available information.

```text
Use case: Low-impact decision with clear fallback
Conditions: Confidence > 0.8, reversible action
```

### ASK

Request specific information from human or system.

```text
Use case: Critical decision point
Conditions: Ambiguous or conflicting state
```

### SEARCH

Query World Model or external sources for required information.

```text
Use case: Information exists but not in working context
Conditions: Searchable entities available
```

### WAIT

Defer decision until information becomes available.

```text
Use case: Real-time state updates expected
Conditions: Non-blocking goal
```

### ESCALATE

Transfer to human for decision.

```text
Use case: High-impact decision with low confidence
Conditions: Budget exhausted or critical uncertainty
```

---

## Uncertainty Response Matrix

| Uncertainty Type | Primary Action | Fallback | Escalation |
|-----------------|---------------|----------|------------|
| Unknown State | SEARCH | ASK | ESCALATE |
| Ambiguous State | ASK | ESCALATE | — |
| Conflicting State | ESCALATE | — | — |
| Stale State | SEARCH | ACT with flag | ASK |
| Missing State | ASK | ESCALATE | — |

---

## Confidence Thresholds

```text
Confidence > 0.9: Proceed with ACT
Confidence 0.7-0.9: Proceed with ACT + flag uncertainty
Confidence 0.5-0.7: Proceed with ASK
Confidence 0.3-0.5: Proceed with ESCALATE
Confidence < 0.3: Block action
```

---

## Uncertainty Documentation

Every plan must document its uncertainty:

```json
{
  "plan_id": "...",
  "plan_steps": [
    {
      "step_id": "1",
      "action": "Move file",
      "target": "launch.json",
      "uncertainty": {
        "type": "ambiguous",
        "confidence": 0.65,
        "candidates": [
          { "path": "/project/vscode/launch.json", "confidence": 0.4 },
          { "path": "/project/scripts/launch.sh", "confidence": 0.35 },
          { "path": "/project/app/launch.py", "confidence": 0.25 }
        ],
        "required_action": "ASK",
        "question": "Which launch file should I move?"
      }
    }
  ],
  "overall_confidence": 0.65,
  "blocking_issues": 1
}
```

---

## Planning with Uncertainty

### Robust Plan Generation

Plans must account for uncertainty:

```text
If uncertainty exists:
    → Include uncertainty resolution steps
    → Provide alternative branches
    → Flag confidence level
```

### Uncertainty-Aware Decomposition

```text
Goal: Move launch file
↓
Step 1: Identify launch file (ASK if ambiguous)
Step 2: Verify destination (SEARCH or ASK)
Step 3: Execute move (ACT)
Step 4: Update references (SEARCH)
Step 5: Verify integrity (SEARCH)
```

---

## EventBus Topics

```text
planner.uncertainty.detected       → Uncertainty identified
planner.uncertainty.classified   → Uncertainty type assigned
planner.uncertainty.action_taken → Response selected
planner.uncertainty.resolved     → Information received
planner.uncertainty.escalated    → Human involvement requested
planner.confidence.updated        → Confidence recalculated
```

---

## Integration with Budget System

When uncertainty leads to repeated queries:

```text
Uncertainty → ASK → SEARCH → WAIT
↓
Budget consumed
↓
If budget exhausted:
    → Escalate
    → Commit to best guess
    → Block action
```

See [10_PLANNING_BUDGET_SPEC.md](10_PLANNING_BUDGET_SPEC.md) for budget limits.

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
| **11** | **Uncertainty & Missing Information** | **This document** |
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
| `10_PLANNING_BUDGET_SPEC.md` | Budget constraints |
| `12_HUMAN_COLLABORATION_MODEL.md` | ASK/ESCALATE mechanisms |
| `14_EXPLAINABILITY_SPEC.md` | Uncertainty documentation |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-10 | Initial draft — Uncertainty & Missing Information |
