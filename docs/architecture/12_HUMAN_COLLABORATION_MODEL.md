# 12 — Human Collaboration Model

**Status:** Proposed (Planner Architecture — Document 12)  
**Authority:** Subordinate to `PROJECT_CONSTITUTION_V4.md` and `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Relation to other docs:** First-class participant specification for Planner (Layer 4)  
**Constitutional constraint:** Planner = Reasoning; Runtime = Execution; World Model = Truth

---

## Purpose

Most agent architectures treat humans as exceptions.

Humans are actually **first-class participants**.

This document defines the interaction patterns between:

```text
Planner ←→ Human ←→ Runtime
```

Without this specification, every future developer invents their own approach.

---

## Interaction Taxonomy

### Need Clarification

The human's intent is unclear or ambiguous.

```text
Planner: "You said 'update the file' — which file?"
Human: "The config.yaml in the settings folder"
```

**Pattern:** Bidirectional query-response

### Need Approval

The action is within scope but requires explicit consent.

```text
Planner: "I plan to delete 47 files. Approve?"
Human: "Yes, proceed"
```

**Pattern:** Blocking wait with response

### Need Preference

Multiple valid options exist; human preference is unknown.

```text
Planner: "I can use either JSON or YAML for the config. Which do you prefer?"
Human: "YAML"
```

**Pattern:** Preference query with stored answer

### Need Confirmation

The plan is ready; human should verify before execution.

```text
Planner: "Here's the plan:
1. Create backup
2. Update config
3. Restart service
Confirm to proceed."
Human: "Confirmed"
```

**Pattern:** Plan presentation with explicit ack

### Need Conflict Resolution

The planner detected conflicting goals or constraints.

```text
Planner: "Goal A and Goal B both require exclusive access to the database.
How should they be ordered?"
Human: "Goal A first"
```

**Pattern:** Mediation with human decision authority

---

## Collaboration Modes

### Synchronous

Human is present and responsive.

```text
Planner → Question → Human → Answer → Planner
```

**Response time:** < 30 seconds  
**Fallback:** Timeout → Escalate

### Asynchronous

Human may be unavailable.

```text
Planner → Question → Queue → Human responds when available
```

**Response time:** Variable  
**Fallback:** Configurable (escalate, use default, or block)

### Background

Human is not involved in real-time.

```text
Planner: "Noted for next interaction"
Human: Reviews history later
```

**Response time:** N/A  
**Fallback:** None (plan stored for later)

---

## Interaction Contract

### Planner Commitments

```text
1. Clearly state what information is needed
2. Explain why the information is needed
3. Present options when multiple exist
4. Indicate urgency and impact
5. Never fabricate or assume without flagging
6. Honor human decisions
```

### Human Commitments

```text
1. Provide clear, unambiguous answers
2. Indicate when information is unavailable
3. Escalate when unable to decide
4. Review flagged items in a timely manner
```

---

## Response Templates

### Clarification Request

```json
{
  "type": "clarification",
  "question": "Which launch file should I move?",
  "options": [
    { "id": "1", "path": "/project/vscode/launch.json", "reason": "Most recently edited" },
    { "id": "2", "path": "/project/scripts/launch.sh", "reason": "Executable script" }
  ],
  "context": "Multiple files named 'launch' found in project",
  "urgency": "blocking",
  "deadline_seconds": 60
}
```

### Approval Request

```json
{
  "type": "approval",
  "action": "Delete 47 files",
  "impact": "high",
  "risk": "medium",
  "affected_entities": ["47 log files", "3 temp directories"],
  "can_revert": true,
  "urgency": "blocking",
  "deadline_seconds": 300
}
```

### Preference Query

```json
{
  "type": "preference",
  "question": "Which format should I use for the config file?",
  "options": [
    { "id": "json", "label": "JSON", "pros": "Universal compatibility", "cons": "Verbose" },
    { "id": "yaml", "label": "YAML", "pros": "Human-readable", "cons": "Indentation-sensitive" }
  ],
  "urgency": "non-blocking",
  "default_if_no_response": "yaml"
}
```

### Confirmation Request

```json
{
  "type": "confirmation",
  "plan": {
    "goal": "Deploy application",
    "steps": [
      { "id": "1", "action": "Create backup", "risk": "low" },
      { "id": "2", "action": "Update config", "risk": "medium" },
      { "id": "3", "action": "Restart service", "risk": "high" }
    ],
    "estimated_duration_seconds": 120,
    "can_cancel": true
  },
  "urgency": "blocking",
  "deadline_seconds": 600
}
```

### Conflict Resolution

```json
{
  "type": "conflict_resolution",
  "conflict": {
    "type": "resource_contention",
    "resource": "database",
    "goals": [
      { "id": "A", "name": "Schema migration", "priority": "normal" },
      { "id": "B", "name": "Backup restore", "priority": "high" }
    ]
  },
  "options": [
    { "id": "1", "description": "Goal B first, then Goal A", "reason": "Higher priority" },
    { "id": "2", "description": "Goal A first, then Goal B", "reason": "Backup can wait" }
  ],
  "urgency": "blocking",
  "deadline_seconds": 120
}
```

---

## Preference Learning

The planner should remember human preferences:

```text
Human: "Use YAML for configs"
    ↓
Planner: Stores preference in Semantic Memory
    ↓
Future: "Which format for config.yaml?"
         → "Based on your preference: YAML"
```

### Preference Types

| Type | Storage | Example |
|------|---------|---------|
| Format | Semantic Memory | "YAML for configs" |
| Style | Semantic Memory | "Tab indentation" |
| Priority | Working Memory | "This project: backups first" |
| Trust Level | Semantic Memory | "Never auto-delete" |

---

## Escalation Paths

When human collaboration fails:

```text
Timeout → Check escalation config
    ↓
If escalation = "use_default":
    → Apply default answer
    → Flag for review
    ↓
If escalation = "use_last":
    → Apply last known answer
    → Flag for confirmation
    ↓
If escalation = "block":
    → Stop planning
    → Request manual intervention
    ↓
If escalation = "escalate_human":
    → Page/notify designated backup human
```

---

## EventBus Topics

```text
planner.human.question       → Question sent to human
planner.human.answer         → Answer received
planner.human.timeout        → No response within deadline
planner.human.preference_set → Preference stored
planner.human.conflict       → Conflict flagged for resolution
planner.human.escalated      → Escalation triggered
```

---

## UI Contract

The UI must support:

```text
1. Question display with options
2. Response input (text, selection, or custom)
3. Deadline visualization
4. Escalation button
5. Preference save toggle
6. Interaction history access
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
| **12** | **Human Collaboration Model** | **This document** |
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
| `11_UNCERTAINTY_AND_MISSING_INFORMATION.md` | ASK/ESCALATE triggers |
| `15_PLANNER_CONSTITUTIONAL_RULES.md` | Collaboration constraints |
| `16_SUCCESS_METRICS_AND_INTELLIGENCE_BENCHMARKS.md` | Collaboration quality metrics |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-10 | Initial draft — Human Collaboration Model |
