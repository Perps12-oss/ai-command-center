# 16 — Success Metrics & Intelligence Benchmarks

**Status:** Proposed (Planner Architecture — Document 16)  
**Authority:** Subordinate to `PROJECT_CONSTITUTION_V4.md` and `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Relation to other docs:** Planner quality measurement for all planning components  
**Constitutional constraint:** Planner = Reasoning; Runtime = Execution; World Model = Truth

---

## Purpose

Without metrics:

```text
"Planner feels smarter"
```

With metrics:

```text
"Planner is smarter"
```

With evidence.

This document defines how we measure whether Planner V7 is actually smarter than Planner V2.

---

## Core Metrics

### Task Success Rate

```text
Percentage of tasks that completed successfully.
```

```python
success_rate = completed_tasks / total_tasks * 100

# Good: > 90%
# Acceptable: > 80%
# Needs improvement: < 80%
```

### Goal Completion Rate

```text
Percentage of user goals that were fully achieved.
```

```python
goal_completion = fully_achieved_goals / total_goals * 100

# Good: > 85%
# Acceptable: > 70%
# Needs improvement: < 70%
```

### Replan Frequency

```text
How often does the planner need to replan?
```

```python
replan_frequency = replans / total_plans * 100

# Good: < 10%
# Acceptable: < 25%
# Needs improvement: > 25%
```

**Note:** High replan frequency indicates planning quality issues.

### Human Intervention Rate

```text
How often does the planner require human help?
```

```python
intervention_rate = interventions / total_plans * 100

# Good: < 15%
# Acceptable: < 30%
# Needs improvement: > 30%
```

**Breakdown:**

```json
{
  "intervention_rate": 0.18,
  "breakdown": {
    "clarification": 0.08,
    "approval_needed": 0.06,
    "conflict_resolution": 0.03,
    "error_recovery": 0.01
  }
}
```

### Approval Denial Rate

```text
How often does the user deny planned actions?
```

```python
denial_rate = denials / approvals_requested * 100

# Good: < 5%
# Acceptable: < 15%
# Needs improvement: > 15%
```

**Note:** High denial rate indicates planning doesn't match user intent.

### False Positive Actions

```text
Actions that planner thought were valid but weren't.
```

```python
false_positive_rate = false_positives / total_actions * 100

# Good: < 2%
# Acceptable: < 5%
# Needs improvement: > 5%
```

### Planning Latency

```text
Time from goal received to plan generated.
```

```python
avg_latency_ms = sum(plan_times) / count
p50_latency_ms = percentile(plan_times, 50)
p95_latency_ms = percentile(plan_times, 95)

# Good: < 2s average, < 5s p95
# Acceptable: < 5s average, < 15s p95
# Needs improvement: > 5s average
```

### Cost Per Goal

```text
Compute/resource cost per goal completion.
```

```json
{
  "cost_per_goal": {
    "tokens_avg": 45000,
    "tokens_p95": 120000,
    "dollars_avg": 0.05,
    "dollars_p95": 0.15
  }
}
```

### Reflection Accuracy

```text
How often was planner self-reflection correct?
```

```python
reflection_accuracy = correct_reflections / total_reflections * 100

# Good: > 80%
# Acceptable: > 60%
# Needs improvement: < 60%
```

### Recovery Success Rate

```text
When plans fail, how often does recovery succeed?
```

```python
recovery_rate = successful_recoveries / failed_plans * 100

# Good: > 90%
# Acceptable: > 75%
# Needs improvement: < 75%
```

---

## Intelligence Score

### Composite Score

```python
def planner_intelligence_score(metrics):
    weights = {
        'task_success': 0.20,
        'goal_completion': 0.20,
        'replan_frequency': 0.10,
        'human_intervention': 0.10,
        'approval_denial': 0.05,
        'planning_latency': 0.10,
        'reflection_accuracy': 0.10,
        'recovery_rate': 0.15
    }
    
    scores = normalize_metrics(metrics)
    weighted_sum = sum(scores[k] * weights[k] for k in weights)
    
    return weighted_sum * 100  # 0-100 scale
```

### Score Levels

| Score | Level | Interpretation |
|-------|-------|----------------|
| 90-100 | Exceptional | Best-in-class planning |
| 80-89 | Excellent | Strong, production-ready |
| 70-79 | Good | Acceptable for most use cases |
| 60-69 | Adequate | Functional but needs work |
| 50-59 | Below Average | Significant gaps |
| < 50 | Poor | Major redesign needed |

---

## Benchmark Scenarios

### Benchmark 1: Simple File Operations

```text
Goal: "Create a backup of config.yaml"
Expected: Single-step plan, < 1s
```

### Benchmark 2: Multi-Step Workflow

```text
Goal: "Update all dependencies and restart the service"
Expected: 3-5 step plan, handles errors
```

### Benchmark 3: Ambiguous Intent

```text
Goal: "Fix the thing that's broken"
Expected: Clarification request or ambiguity flag
```

### Benchmark 4: Constraint Satisfaction

```text
Goal: "Refactor the module" with constraints:
- No breaking changes
- Must pass tests
- Max 2 hours
Expected: Constrained plan with verification steps
```

### Benchmark 5: Conflicting Goals

```text
Goals: 
- "Deploy to production"
- "Keep system available"
Expected: Conflict detection and resolution
```

### Benchmark 6: Large-Scale Change

```text
Goal: "Migrate database schema"
Expected: Phased plan with rollback, checkpoints
```

### Benchmark 7: Recovery Scenario

```text
Goal: "Complete X" with mid-plan failure
Expected: Recovery plan within budget
```

### Benchmark 8: Uncertainty Handling

```text
Goal: "Update the config" with missing state
Expected: State discovery or clarification
```

---

## Benchmark Scoring

```python
benchmark_results = {
    "simple_file_ops": {
        "score": 0.95,
        "latency_ms": 450,
        "success": True
    },
    "multi_step_workflow": {
        "score": 0.88,
        "latency_ms": 2300,
        "success": True
    },
    "ambiguous_intent": {
        "score": 0.92,
        "clarification_requested": True,
        "success": True
    },
    # ... etc
}

def overall_benchmark_score(results):
    return mean([r["score"] for r in results.values()])
```

---

## Tracking Over Time

### Weekly Metrics

```json
{
  "week": "2026-W28",
  "metrics": {
    "task_success_rate": 0.91,
    "goal_completion_rate": 0.87,
    "replan_frequency": 0.12,
    "human_intervention_rate": 0.15,
    "planner_intelligence_score": 84.2
  },
  "benchmark_score": 0.89,
  "trends": {
    "task_success": "+2%",
    "latency": "-15%",
    "intervention": "-3%"
  }
}
```

### Version Comparison

```json
{
  "versions": {
    "v2": { "score": 72.3, "date": "2026-01" },
    "v4": { "score": 78.1, "date": "2026-04" },
    "v7": { "score": 84.2, "date": "2026-07" }
  },
  "improvement_v2_to_v7": "+16.5%"
}
```

---

## Goal-Based Metrics

### Per-Goal-Type Analysis

```json
{
  "by_goal_type": {
    "file_operations": {
      "success_rate": 0.95,
      "avg_latency_ms": 800
    },
    "code_changes": {
      "success_rate": 0.88,
      "avg_latency_ms": 4500
    },
    "config_updates": {
      "success_rate": 0.92,
      "avg_latency_ms": 1200
    },
    "system_maintenance": {
      "success_rate": 0.85,
      "avg_latency_ms": 8000
    }
  }
}
```

### Per-User Analysis

```json
{
  "by_user_pattern": {
    "precise_instructions": {
      "success_rate": 0.95,
      "intervention_rate": 0.08
    },
    "vague_instructions": {
      "success_rate": 0.72,
      "intervention_rate": 0.35
    }
  }
}
```

---

## EventBus Topics

```text
metrics.planner.generated     → Metrics collected
metrics.benchmark.started   → Benchmark run started
metrics.benchmark.complete  → Benchmark run completed
metrics.score.updated       → Intelligence score recalculated
metrics.alert.triggered     → Metric threshold exceeded
```

---

## Dashboard Requirements

The metrics system should support:

```text
1. Real-time metric display
2. Historical trend charts
3. Version comparison views
4. Benchmark results
5. Goal-type breakdowns
6. Alert configurations
7. Export capabilities
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
| 14 | Explainability Specification | — |
| 15 | Planner Constitutional Rules | — |
| **16** | **Success Metrics & Intelligence Benchmarks** | **This document** |
| 17 | State Projection & Simulation | — |
| 18 | Context & Memory Externalization | — |
| 19 | World Model Query and Reasoning | — |

---

## References

| Document | Role |
|----------|------|
| `PROJECT_CONSTITUTION_V4.md` | Supreme authority |
| `VNEXT_STATE_DRIVEN_BLUEPRINT.md` | Cognitive stack architecture |
| `10_PLANNING_BUDGET_SPEC.md` | Budget optimization targets |
| `14_EXPLAINABILITY_SPEC.md` | Explanation quality tracking |
| `15_PLANNER_CONSTITUTIONAL_RULES.md` | Constitutional compliance |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-10 | Initial draft — Success Metrics & Intelligence Benchmarks |
