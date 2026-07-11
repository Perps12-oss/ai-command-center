# Phase 9: Goals, Planning & Multi-Agent Coordination

**Status:** PLANNED  
**Priority:** HIGH  
**Estimated Effort:** 8-10 weeks  
**Dependencies:** Phase 8 (Operator Kernel) ✅  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `AGENTS.md`

---

## Mission

Transform ACC from **Command Execution System** into **Goal Driven Workspace OS**.

```
Current:
User Request → Execute → Done

Future:
Goal → Plan → Execute → Monitor → Adapt → Complete
```

---

## Core Principle

```
Commands are temporary.
Goals persist.
```

---

## Architecture

```
Goal
  │
  ▼
Planner
  │
  ▼
Task Graph
  │
  ▼
Execution Coordinator
  │
  ▼
Specialist Agents
  │
  ▼
Timeline
```

---

## Major Subsystems

### 9.1 Goal Engine

**New Entity:**

```python
@dataclass
class Goal:
    id: str
    title: str
    description: str
    status: GoalStatus  # ACTIVE, PAUSED, COMPLETED, ABANDONED
    created_at: datetime
    updated_at: datetime
    created_by: str
    parent_goal_id: str | None
    tags: list[str]
    metadata: dict
```

**Goals survive restarts.**

**Examples:**
- "Modernize Chat UI"
- "Implement Phase 8"
- "Audit Repository"
- "Create Release Candidate"

### 9.2 Planning Engine

**Reference:** Iterative Planner concepts

**Pipeline:**

```
Goal
  │
  ▼
Explore (understand context)
  │
  ▼
Plan (generate task graph)
  │
  ▼
Validate (check feasibility)
  │
  ▼
Execute (run tasks)
  │
  ▼
Review (assess progress)
  │
  ▼
Close (complete or archive)
```

**Output:**

```python
@dataclass
class ExecutionPlan:
    goal_id: str
    tasks: list[Task]
    estimated_duration: timedelta
    risks: list[str]
    approvals_required: list[ApprovalRequest]
```

### 9.3 Task Graph System

**Replace task lists with DAG structure.**

```python
@dataclass
class Task:
    id: str
    goal_id: str
    title: str
    description: str
    status: TaskStatus  # PENDING, BLOCKED, IN_PROGRESS, COMPLETED, FAILED
    dependencies: list[str]  # Task IDs
    assignee: str | None
    priority: int
    created_at: datetime
    completed_at: datetime | None
```

**Allows:**
- Dependencies
- Blocking
- Parallel work
- Critical path analysis

### 9.4 Agent Contract Framework

**Every agent declares:**

```python
@dataclass
class AgentContract:
    agent_id: str
    capabilities: list[Capability]
    permissions: list[Permission]
    dependencies: list[str]  # Other agents
    risk_level: RiskLevel
    evidence_requirements: list[str]
    max_concurrent_tasks: int
```

**Example Agents:**

| Agent | Capabilities | Risk Level |
|-------|-------------|------------|
| `AuditAgent` | code_analysis, repository_audit | LOW |
| `ResearchAgent` | web_search, documentation_review | LOW |
| `WorkflowAgent` | task_execution, state_management | MEDIUM |
| `CodingAgent` | code_generation, refactoring, testing | HIGH |

### 9.5 Coordination Engine

**New Service:** `ai_command_center/orchestration/agents/agent_coordinator.py`

**Responsibilities:**
- Task assignment based on capabilities
- Work distribution across agents
- Result aggregation
- Conflict resolution
- Deadlock detection

**Operator remains supervisor. Agents never become autonomous rulers.**

### 9.6 Policy Engine

**Before agent execution:**

```python
class PolicyCheck:
    CAN_EXECUTE = "Agent has capability and permission"
    CANNOT_EXECUTE_NO_CAPABILITY = "Capability not in agent contract"
    CANNOT_EXECUTE_NO_PERMISSION = "Permission denied"
    REQUIRES_APPROVAL = "High-risk action requires user approval"
```

### 9.7 Operational Memory

**Built from:**
- Timeline events
- Goals
- Tasks
- Results

**Not chat history.**

**Survives sessions.**

---

## EventBus Topics

| Topic | Direction | Payload |
|-------|-----------|---------|
| `goal.created` | Outbound | `{ goal: Goal }` |
| `goal.updated` | Outbound | `{ goal_id, changes }` |
| `goal.completed` | Outbound | `{ goal_id, summary }` |
| `plan.requested` | Inbound | `{ goal_id, context }` |
| `plan.generated` | Outbound | `{ goal_id, plan: ExecutionPlan }` |
| `task.assigned` | Outbound | `{ task_id, agent_id }` |
| `task.completed` | Inbound | `{ task_id, result }` |
| `agent.spawned` | Outbound | `{ agent_id, contract }` |
| `agent.terminated` | Outbound | `{ agent_id, reason }` |

---

## Success Criteria

- [ ] ACC manages long-running goals
- [ ] Plans survive restarts
- [ ] Multiple agents collaborate
- [ ] Operator remains authority
- [ ] Every agent action is auditable
- [ ] Goal progress visible in UI

---

## Files

### Create

```
ai_command_center/orchestration/goals/
├── __init__.py
├── goal_engine.py
├── goal.py
├── goal_status.py
├── planning_engine.py
├── task_graph.py
├── task.py
├── execution_plan.py
└── agent_coordinator.py

ai_command_center/orchestration/agents/
├── __init__.py
├── agent_contract.py
├── agent_registry.py
├── agent_spawner.py
├── agent_policy_engine.py
└── agent_lifecycle.py

ai_command_center/operator/ (from Phase 8)
├── __init__.py
└── ...

tests/orchestration/goals/
├── __init__.py
├── test_goal_engine.py
├── test_task_graph.py
├── test_planning_pipeline.py
├── test_execution_plan.py
└── test_goal_persistence.py

tests/orchestration/agents/
├── __init__.py
├── test_agent_coordinator.py
├── test_agent_contracts.py
├── test_agent_lifecycle.py
└── test_policy_engine.py
```

### Modify

```
ai_command_center/core/events/topics.py
ai_command_center/repositories/
ai_command_center/ui/views/
```

---

## Exit Criteria

- [ ] Goals persist across restarts
- [ ] Task graph supports dependencies
- [ ] Multiple agents can collaborate on same goal
- [ ] Operator approval required for high-risk tasks
- [ ] Timeline shows complete audit trail
- [ ] Architecture lint clean
- [ ] UCGS PASS

---

## Non-Goals

- Autonomous ReAct loops (User Goal → Plan → Execute → Stop only)
- Agent-to-agent direct communication
- Agent persistence beyond session
- Real-time agent collaboration UI

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial plan |
