# 14 — Explainability Specification

**Status:** Proposed (Planner Architecture — Document 14)  
**Authority:** Subordinate to `PROJECT_CONSTITUTION_V4.md` and `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Relation to other docs:** Planner transparency for Planner (Layer 4)  
**Constitutional constraint:** Planner = Reasoning; Runtime = Execution; World Model = Truth

---

## Purpose

Every plan should answer:

```text
Why?
Why now?
Why this plan?
Why not the alternatives?
```

Future you will thank present you when debugging.

Without explainability:

```text
Planner: "I did X"
Developer: "Why?"
Planner: "..."
```

With explainability:

```text
Planner: "I did X because Y. I considered A, B, C but chose X due to constraint Z."
```

---

## Explainability Contract

Every plan output must include:

```json
{
  "plan": {
    "id": "plan_uuid",
    "goal": "...",
    "steps": [...]
  },
  "explanation": {
    "why": "...",
    "why_now": "...",
    "why_this_plan": "...",
    "why_not_alternatives": [...],
    "constraints_applied": [...],
    "assumptions": [...],
    "confidence": 0.82,
    "uncertainty_flagged": [...]
  }
}
```

---

## Explanation Components

### Why

Why is this goal being pursued?

```text
Examples:
- "User explicitly requested this goal"
- "Goal unblocks higher-priority work"
- "Automated trigger detected condition"
```

### Why Now

Why is this goal being planned at this moment?

```text
Examples:
- "User triggered immediately"
- "Deadline approaching (2 hours)"
- "Resource became available"
- "Prerequisite goal just completed"
```

### Why This Plan

Why was this specific plan chosen?

```text
Examples:
- "Lowest risk approach"
- "Matches user's preferred pattern"
- "Optimizes for speed within constraints"
- "Follows established project conventions"
```

### Why Not Alternatives

Why were alternative plans rejected?

```json
{
  "alternatives_considered": [
    {
      "plan": "Alternative A",
      "rejected_reason": "Higher risk (file deletion)",
      "tradeoff": "Speed vs. Safety"
    },
    {
      "plan": "Alternative B",
      "rejected_reason": "Exceeded budget (50 nodes vs 25 max)",
      "tradeoff": "Completeness vs. Constraints"
    },
    {
      "plan": "Alternative C",
      "rejected_reason": "Requires unavailable resource (database lock)",
      "tradeoff": "Scope vs. Resources"
    }
  ]
}
```

### Constraints Applied

Which constraints influenced the plan?

```json
{
  "constraints_applied": [
    {
      "constraint": "Max DAG Nodes = 25",
      "effect": "Simplified plan from 30 steps to 22 steps"
    },
    {
      "constraint": "No file deletion",
      "effect": "Chose 'archive' over 'delete' for old logs"
    },
    {
      "constraint": "User preference: YAML configs",
      "effect": "Selected YAML format over JSON"
    }
  ]
}
```

### Assumptions

What assumptions does the plan rely on?

```json
{
  "assumptions": [
    {
      "assumption": "File exists at expected path",
      "confidence": 0.95,
      "can_verify": true,
      "verification_step": "Step 1 will verify file existence"
    },
    {
      "assumption": "Network connectivity maintained",
      "confidence": 0.99,
      "can_verify": false,
      "risk_mitigation": "Step 3 has timeout and retry"
    }
  ]
}
```

### Confidence Score

Overall confidence in plan success.

```json
{
  "confidence": 0.82,
  "factors": {
    "state_completeness": 0.9,
    "constraint_alignment": 0.95,
    "resource_availability": 0.85,
    "historical_success_rate": 0.78
  }
}
```

### Uncertainty Flagged

Explicitly flagged uncertainties.

```json
{
  "uncertainty_flagged": [
    {
      "type": "ambiguous",
      "description": "Multiple 'launch' files found",
      "resolution": "Human clarification requested",
      "blocked": true
    },
    {
      "type": "stale",
      "description": "Workspace model may be outdated",
      "resolution": "Fresh state will be verified",
      "blocked": false
    }
  ]
}
```

---

## Step-Level Explanations

Each plan step should also be explainable:

```json
{
  "steps": [
    {
      "step_id": "1",
      "action": "Verify file exists",
      "explanation": "Prerequisite check before modification",
      "confidence": 0.99,
      "can_undo": "N/A (read-only)"
    },
    {
      "step_id": "2",
      "action": "Create backup",
      "explanation": "Safety measure before destructive operation",
      "confidence": 0.98,
      "can_undo": true
    },
    {
      "step_id": "3",
      "action": "Modify file",
      "explanation": "Required for goal; lower-risk than alternative (delete + recreate)",
      "confidence": 0.90,
      "can_undo": true
    }
  ]
}
```

---

## Plan Traceability

### Decision Log

Every significant decision should be traceable:

```json
{
  "decisions": [
    {
      "decision_id": "d1",
      "point": "Step ordering",
      "options_considered": ["A then B", "B then A"],
      "chosen": "A then B",
      "reason": "A creates resource needed by B",
      "timestamp": "2026-07-10T10:30:00Z"
    },
    {
      "decision_id": "d2",
      "point": "Tool selection",
      "options_considered": ["tool.edit", "tool.write", "manual edit"],
      "chosen": "tool.edit",
      "reason": "Preserves file permissions and encoding",
      "timestamp": "2026-07-10T10:30:05Z"
    }
  ]
}
```

### Reasoning Chain

Human-readable reasoning chain:

```text
Goal: Update configuration

Reasoning:
1. User requested config update
2. Checked current config structure
3. Identified change needed: add new key
4. Evaluated tools: tool.edit preserves structure
5. Applied change with backup
6. Verified change applied correctly

Plan chosen because:
- Minimal risk (edit, not replace)
- Preserves metadata
- Reversible (backup exists)
- Matches project convention (use tool.edit)
```

---

## User-Facing Explanations

Present explanations at appropriate abstraction levels:

### Summary (One Line)

```text
"Updated config.yaml to add the new API endpoint"
```

### Brief (One Paragraph)

```text
"Added the 'api_endpoint' key to config.yaml using tool.edit.
I chose this approach because it preserves file formatting and creates
a backup first. Alternative (replace entire file) was rejected due to
higher risk of metadata loss."
```

### Detailed (Full Trace)

```text
"Added 'api_endpoint' to config.yaml.
- Why: User requested this configuration change
- How: tool.edit (preserves formatting)
- Safety: Backup created at config.yaml.backup
- Alternatives considered:
  - tool.write: Rejected (loses formatting)
  - manual: Rejected (requires user presence)
- Confidence: 92%
- Uncertainty: None flagged
"
```

---

## EventBus Topics

```text
planner.explanation.generated    → Explanation attached to plan
planner.explanation.requested   → User requested explanation
planner.explanation.updated     → Explanation refined
planner.decision.logged         → Decision recorded
planner.uncertainty.flagged    → Uncertainty documented
```

---

## Debugging Integration

Explanations enable debugging:

```text
User: "Why did the plan fail?"
    ↓
System: Shows plan explanation
    ↓
Highlights:
- Which assumption failed
- Which constraint was violated
- Where uncertainty was unresolved
    ↓
Future: "Why didn't you account for X?"
System: "Because X was not in the state model"
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
| 13 | Goal Arbitration | — |
| **14** | **Explainability Specification** | **This document** |
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
| `11_UNCERTAINTY_AND_MISSING_INFORMATION.md` | Uncertainty documentation |
| `15_PLANNER_CONSTITUTIONAL_RULES.md` | Transparency constraints |
| `16_SUCCESS_METRICS_AND_INTELLIGENCE_BENCHMARKS.md` | Explanation quality metrics |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-10 | Initial draft — Explainability Specification |
