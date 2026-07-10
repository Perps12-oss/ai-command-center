# 04 — Constraint Engine Specification

**Status:** Phase C0 — Constitution (Authoritative Specification)  
**Authority:** Subordinate to `PROJECT_CONSTITUTION_V4.md` and `01_PLANNER_ARCHITECTURE.md`  
**Purpose:** Define how constraints are defined, evaluated, and enforced in planning

---

## Purpose

Define the constraint system that governs what the Planner can and cannot propose. Constraints are the boundaries within which planning occurs.

---

## Responsibilities

### Core Responsibilities

1. **Constraint Definition** — Define the vocabulary for expressing constraints
2. **Constraint Evaluation** — Check plan compliance with constraints
3. **Conflict Resolution** — Handle conflicting constraints
4. **Violation Handling** — Determine response to constraint violations
5. **Constraint Propagation** — Derive implied constraints

### Non-Responsibilities

| Not Owned By | Owned By |
|-------------|----------|
| User preferences | Human Collaboration Model |
| Capability limits | Capability Registry |
| Approval rules | Runtime |
| Safety policies | Runtime Safety |

---

## Constraint Taxonomy

### Hard Constraints

Constraints that **must** be satisfied. Violation = rejection.

```json
{
  "constraint": {
    "constraintId": "uuid",
    "type": "HARD",
    "category": "SAFETY",
    "name": "NoAutoDelete",
    "description": "Files may not be automatically deleted without explicit human approval",
    "expression": {
      "type": "FORBIDDEN",
      "action": "file.delete",
      "conditions": [
        {
          "type": "automatic_trigger",
          "value": true
        }
      ]
    },
    "enforcement": "STRICT",
    "overrideable": false
  }
}
```

### Soft Constraints

Constraints that **should** be satisfied. Violation = penalty or warning.

```json
{
  "constraint": {
    "constraintId": "uuid",
    "type": "SOFT",
    "category": "PREFERENCE",
    "name": "PreferReversibleActions",
    "description": "Prefer reversible actions over irreversible ones",
    "expression": {
      "type": "PREFERENCE",
      "action": "any",
      "weight": 0.3,
      "scoring": {
        "reversible": 1.0,
        "partially_reversible": 0.5,
        "irreversible": 0.0
      }
    },
    "enforcement": "WEIGHTED"
  }
}
```

### User Constraints

Constraints derived from user preferences or explicit requirements.

```json
{
  "constraint": {
    "constraintId": "uuid",
    "type": "USER",
    "category": "PREFERENCE",
    "name": "PreferredFormat",
    "description": "User prefers YAML format for configuration files",
    "source": "user_preference",
    "expression": {
      "type": "PREFERENCE",
      "action": "file.create",
      "parameters": {
        "format": "yaml"
      },
      "weight": 0.5
    },
    "confidence": 0.9
  }
}
```

### System Constraints

Constraints derived from system configuration or policies.

```json
{
  "constraint": {
    "constraintId": "uuid",
    "type": "SYSTEM",
    "category": "RESOURCE",
    "name": "MemoryLimit",
    "description": "Maximum memory usage per operation",
    "expression": {
      "type": "LIMIT",
      "resource": "memory",
      "max": "1GB"
    },
    "enforcement": "STRICT"
  }
}
```

### Safety Constraints

Constraints that protect system integrity and user safety.

```json
{
  "constraint": {
    "constraintId": "uuid",
    "type": "SAFETY",
    "category": "CRITICAL",
    "name": "ApprovalRequiredForDestructive",
    "description": "Destructive operations require explicit human approval",
    "expression": {
      "type": "REQUIRE_APPROVAL",
      "actions": [
        "file.delete",
        "data.delete",
        "system.modify"
      ]
    },
    "enforcement": "STRICT",
    "overrideable": false
  }
}
```

### Policy Constraints

Constraints derived from organizational or project policies.

```json
{
  "constraint": {
    "constraintId": "uuid",
    "type": "POLICY",
    "category": "COMPLIANCE",
    "name": "AuditRequired",
    "description": "All data modifications must be auditable",
    "expression": {
      "type": "REQUIRE_LOGGING",
      "actions": ["data.modify", "config.change"]
    },
    "enforcement": "STRICT"
  }
}
```

---

## Constraint Examples

### Never Delete Files Automatically

```json
{
  "constraint": {
    "constraintId": "uuid",
    "type": "HARD",
    "name": "NoAutomaticFileDeletion",
    "description": "Files may not be deleted automatically without explicit user approval",
    "expression": {
      "type": "FORBIDDEN",
      "action": "file.delete",
      "conditions": [{
        "type": "trigger",
        "value": "automatic"
      }]
    },
    "enforcement": "STRICT"
  }
}
```

### Never Spend Money Automatically

```json
{
  "constraint": {
    "constraintId": "uuid",
    "type": "HARD",
    "name": "NoAutomaticSpending",
    "description": "No financial transactions without explicit user approval",
    "expression": {
      "type": "FORBIDDEN",
      "action": "payment.execute",
      "conditions": [{
        "type": "trigger",
        "value": "automatic"
      }]
    },
    "enforcement": "STRICT"
  }
}
```

### Only Operate Inside Approved Directories

```json
{
  "constraint": {
    "constraintId": "uuid",
    "type": "HARD",
    "name": "DirectoryScopeRestriction",
    "description": "All file operations must be within approved workspace directories",
    "expression": {
      "type": "SCOPE",
      "actions": ["file.*", "directory.*"],
      "allowedScopes": ["${workspace}", "${temp}"],
      "blockedScopes": ["${system}", "${protected}"]
    },
    "enforcement": "STRICT"
  }
}
```

### Never Modify Calendars Without Approval

```json
{
  "constraint": {
    "constraintId": "uuid",
    "type": "HARD",
    "name": "CalendarApprovalRequired",
    "description": "Calendar modifications require explicit user approval",
    "expression": {
      "type": "REQUIRE_APPROVAL",
      "actions": ["calendar.create", "calendar.modify", "calendar.delete"]
    },
    "enforcement": "STRICT"
  }
}
```

---

## Constraint Resolution

### Priority Resolution

When constraints conflict, priority determines resolution.

```json
{
  "priorityResolution": {
    "hierarchy": [
      "SAFETY",    // Highest priority
      "CRITICAL", 
      "POLICY",
      "HARD",
      "SYSTEM",
      "USER",
      "SOFT"       // Lowest priority
    ],
    "rule": "Higher priority constraint wins"
  }
}
```

### Conflict Resolution

```python
def resolve_conflicts(constraints):
    # Sort by priority
    sorted_constraints = sorted(
        constraints, 
        key=lambda c: c.priority, 
        reverse=True
    )
    
    # Identify conflicts
    conflicts = find_conflicts(sorted_constraints)
    
    resolved = []
    for conflict in conflicts:
        # Higher priority wins
        winner = conflict.higher_priority_constraint
        resolved.append(winner)
        
        # Log resolution
        log_constraint_resolution(
            conflict=conflict,
            winner=winner,
            reason=f"Priority: {winner.type} > {conflict.lower_priority_constraint.type}"
        )
    
    return resolved
```

### Escalation Rules

```json
{
  "escalationRules": {
    "unresolvable_conflict": {
      "condition": "conflicting_constraints cannot be satisfied",
      "action": "ESCALATE",
      "target": "human_collaboration"
    },
    "constraint_unknown": {
      "condition": "constraint applicability unclear",
      "action": "ASK",
      "question": "Does this constraint apply to the current situation?"
    },
    "override_requested": {
      "condition": "user requests override",
      "action": "REQUIRE_EXPLICIT_APPROVAL",
      "warning": "Overriding this constraint may have unintended consequences"
    }
  }
}
```

### Violation Handling

```python
def handle_violation(constraint, plan, violation):
    if constraint.type == "HARD":
        # Hard constraints cannot be violated
        return ViolationResponse(
            action="REJECT",
            plan=plan,
            reason=f"Hard constraint violated: {constraint.name}",
            resolution="replan_required"
        )
    
    elif constraint.type == "SOFT":
        # Soft constraints get penalties
        penalty = calculate_penalty(constraint, violation)
        return ViolationResponse(
            action="PENALIZE",
            plan=plan,
            penalty=penalty,
            reason=f"Soft constraint violated: {constraint.name}"
        )
    
    elif constraint.type == "USER":
        # User constraints get warnings
        return ViolationResponse(
            action="WARN",
            plan=plan,
            reason=f"User preference not followed: {constraint.name}",
            alternative="Consider respecting this preference"
        )
```

---

## Constraint Evaluation

### Evaluation Engine

```python
class ConstraintEngine:
    def evaluate_plan(self, plan, constraints):
        results = {
            "hard_satisfied": [],
            "hard_violated": [],
            "soft_satisfied": [],
            "soft_violated": [],
            "warnings": [],
            "overall_valid": True
        }
        
        for constraint in constraints:
            result = self.evaluate_constraint(plan, constraint)
            
            if constraint.type == "HARD":
                if result.satisfied:
                    results["hard_satisfied"].append(constraint)
                else:
                    results["hard_violated"].append(constraint)
                    results["overall_valid"] = False
            
            elif constraint.type == "SOFT":
                if result.satisfied:
                    results["soft_satisfied"].append(constraint)
                else:
                    results["soft_violated"].append(constraint)
        
        return ConstraintEvaluationResult(**results)
    
    def evaluate_constraint(self, plan, constraint):
        # Constraint-specific evaluation
        pass
```

### Evaluation Metrics

```json
{
  "constraintMetrics": {
    "hardConstraintSatisfaction": {
      "formula": "satisfied_hard / total_hard * 100",
      "target": "100%",
      "critical": true
    },
    "softConstraintSatisfaction": {
      "formula": "satisfied_soft / total_soft * 100",
      "target": ">80%",
      "critical": false
    },
    "constraintConflictRate": {
      "formula": "conflicts / total_evaluations * 100",
      "target": "<5%",
      "critical": false
    },
    "escalationRate": {
      "formula": "escalations / total_evaluations * 100",
      "target": "<2%",
      "critical": false
    }
  }
}
```

---

## Required Decisions

### Constraint Precedence

```yaml
constraint_precedence:
  order:
    - SAFETY
    - CRITICAL
    - POLICY
    - HARD
    - SYSTEM
    - USER
    - SOFT
  
  resolution:
    same_priority_conflict: escalate
    different_priority_conflict: higher_wins
    unresolvable: escalate
```

### Override Mechanisms

```yaml
override_mechanisms:
  hard_constraints:
    override_allowed: false
  
  safety_constraints:
    override_allowed: false
  
  policy_constraints:
    override_allowed: true
    requires_explicit_approval: true
    audit_log_required: true
  
  soft_constraints:
    override_allowed: true
    penalty_applied: true
    warning_generated: true
```

### Human Approval Requirements

```json
{
  "approvalRequirements": {
    "hardConstraintViolation": {
      "requiresApproval": true,
      "approver": "human",
      "timeout": 300,
      "escalation": "timeout → reject"
    },
    "safetyOverride": {
      "requiresApproval": true,
      "approver": "human",
      "warningRequired": true,
      "auditRequired": true
    },
    "policyOverride": {
      "requiresApproval": true,
      "approver": "authorized_user",
      "justificationRequired": true
    }
  }
}
```

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|------------|
| CE-001 | Hard constraints are non-violable | Safety requirement |
| CE-002 | Priority hierarchy defined | Enables conflict resolution |
| CE-003 | Safety constraints cannot be overridden | Critical protection |
| CE-004 | Constraint violations are logged | Audit trail |
| CE-005 | Escalation for unresolvable conflicts | Human judgment when automated fails |

---

## Tradeoffs

### Benefits

1. **Safety** — Prevents dangerous actions
2. **Predictability** — Consistent constraint enforcement
3. **Flexibility** — Supports various constraint types
4. **Auditability** — All constraint decisions logged
5. **User Control** — User preferences respected

### Costs

1. **Complexity** — Multiple constraint types to manage
2. **Performance** — Evaluation adds latency
3. **Maintenance** — Constraint definitions need upkeep
4. **Conflict Potential** — Constraints may conflict

---

## Failure Modes

| Mode | Detection | Impact | Recovery |
|------|-----------|--------|----------|
| Unresolvable conflict | Evaluation | Cannot plan | Escalate |
| Constraint not found | Lookup | Incomplete evaluation | Log warning |
| Evaluation timeout | Timeout | Partial evaluation | Use best available |
| Constraint engine failure | Exception | No evaluation | Fallback to no constraints |

---

## Recovery Strategy

```python
def recover_from_constraint_failure(failure):
    if failure == "UNRESOLVABLE_CONFLICT":
        return escalate_to_human()
    elif failure == "CONSTRAINT_NOT_FOUND":
        return log_and_continue()
    elif failure == "EVALUATION_TIMEOUT":
        return use_partial_evaluation()
    elif failure == "ENGINE_FAILURE":
        return fallback_to_basic_constraints()
    else:
        return escalate_to_human()
```

---

## Future Evolution Path

### Phase C1: Learned Constraints

- Infer constraints from user behavior
- Adapt constraints over time
- Learn from constraint violations

### Phase C2: Distributed Constraints

- Share constraints across workspaces
- Support team-level policies
- Enable constraint inheritance

### Phase C3: Probabilistic Constraints

- Support uncertainty in constraints
- Enable constraint relaxation
- Add constraint confidence levels

---

## References

| Document | Role |
|----------|------|
| `PROJECT_CONSTITUTION_V4.md` | Supreme authority |
| `01_PLANNER_ARCHITECTURE.md` | Planner requirements |
| `12_HUMAN_COLLABORATION_MODEL.md` | Override mechanisms |
| `RUNTIME_SAFETY.md` | Safety constraints |

---

## Revision History

| Date | Change | Author |
|------|--------|--------|
| 2026-07-10 | Initial C0 Constitution | ACC Planner Evolution Program |
