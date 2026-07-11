# Phase 7-10: Key Questions & Answers

**Status:** ACTIVE  
**Authority:** `PROJECT_CONSTITUTION_V4.md`  
**Purpose:** Document critical questions and answers for Phases 7-10 implementation

---

## Question 1: Model Independence (Phase 8)

### Q: How does ACC maintain consistent operator behavior across different LLM providers (GPT, Claude, Gemini, Qwen, DeepSeek, Llama)?

### A: Behavior Belongs to ACC, Reasoning Belongs to LLM

The Operator Kernel is the **single source of truth** for operational behavior. LLMs only provide reasoning capabilities while ACC controls governance.

```
┌─────────────────────────────────────────────────────────────┐
│                    OPERATOR KERNEL                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Behavior │ Rules │ Governance │ Compliance         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │     MODEL ADAPTER LAYER     │
              │  ┌─────┐ ┌─────┐ ┌─────┐  │
              │  │ GPT │ │Claude│ │Qwen │  │
              │  └─────┘ └─────┘ └─────┘  │
              └─────────────────────────────┘
```

### Implementation Details

| Component | Responsibility |
|-----------|----------------|
| **OperatorKernel** | Owns all operational behavior |
| **IntentResolver** | Classifies intent (ACC rule) |
| **ModeResolver** | Determines mode (ACC rule) |
| **PromptAssemblyService** | Builds prompts in layers (ACC rule) |
| **ModelAdapter** | Translates to provider format only |
| **ComplianceEngine** | Validates all outputs |

### Key Guarantees

1. **No prompt rewrites needed** when swapping models
   - Prompts are assembled by ACC, not model-specific
   - Model only sees structured input

2. **Same behavior across providers**
   - Response contracts are enforced
   - ComplianceEngine catches deviations

3. **No capability changes**
   - Capabilities are defined in ACC registry
   - Models don't introduce new capabilities

### Verification

```python
# Model Independence Score
ModelIndependenceScore(
    behavior_consistency: 0.97,  # Same commands across models
    hallucination_resistance: 0.99,  # Compliance catches 99%
    contract_compliance: 0.98,  # 98% contract adherence
)
```

---

## Question 2: Goal Persistence (Phase 9)

### Q: How do goals survive restarts and persist across sessions in the goal-driven architecture?

### A: Goals Are Entities, Stored in SQLite

Goals are first-class entities with full lifecycle management:

```python
@dataclass
class Goal:
    id: str                    # UUID
    title: str                 # Human-readable
    description: str           # Detailed description
    status: GoalStatus          # ACTIVE, PAUSED, COMPLETED, ABANDONED
    created_at: datetime      # Immutable
    updated_at: datetime       # Auto-updated
    created_by: str            # User/Agent ID
    parent_goal_id: str | None # For sub-goals
    tags: list[str]            # For filtering
    metadata: dict             # Flexible storage
```

### Persistence Architecture

```
┌──────────────┐
│  GoalEngine  │  ← Service layer
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────┐
│     GoalRepository              │  ← Repository pattern
│  ┌─────────────────────────┐   │
│  │ SQLite: goals table     │   │  ← Persistence
│  │ - Goals survive restart │   │
│  │ - Indexed by status     │   │
│  │ - Full-text search      │   │
│  └─────────────────────────┘   │
└─────────────────────────────────┘
```

### Task Graph Persistence

```python
@dataclass  
class Task:
    id: str
    goal_id: str              # Links to parent goal
    status: TaskStatus
    dependencies: list[str]   # DAG structure
    assignee: str | None
    priority: int
    
# Stored in: tasks table
# goal_id creates foreign key relationship
# Dependencies create graph structure
```

### Restart Recovery

1. **On startup:**
   - GoalEngine loads all ACTIVE goals
   - Rebuilds TaskGraph from stored dependencies
   - Resumes any IN_PROGRESS tasks

2. **During operation:**
   - Every state change persists immediately
   - Checkpointing after each task completion

3. **Recovery scenarios:**
   - Crash → Resume from last checkpoint
   - Restart → Load goals, rebuild state
   - Migration → Goals survive schema changes

### Example Flow

```
User: "Implement Phase 8"
  │
  ▼
GoalEngine.create_goal(title="Implement Phase 8")
  │
  ▼
SQLite INSERT: goals table
  │
  ▼
Planner.create_tasks(goal_id)
  │
  ▼
SQLite INSERT: tasks table (with goal_id foreign key)
  │
  ▼
[RESTART OCCURS]
  │
  ▼
GoalEngine.load_active_goals()
  │
  ▼
TaskGraph.rebuild_from_db(goal_id)
  │
  ▼
Continue execution
```

---

## Question 3: Multi-Agent Coordination (Phase 9)

### Q: How do agents collaborate without becoming autonomous rulers? What prevents agent dominance?

### A: Operator Remains Supervisor, Agents Are Tools

```
┌─────────────────────────────────────────────────────────────┐
│                      OPERATOR                               │
│                    (The Authority)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • Approves high-risk actions                      │   │
│  │  • Assigns tasks to agents                        │   │
│  │  • Reviews agent results                          │   │
│  │  • Can terminate any agent                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  AGENT COORDINATOR                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • Task assignment                                 │   │
│  │  • Work distribution                               │   │
│  │  • Result aggregation                              │   │
│  │  • Conflict resolution                             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
         ┌─────────┐  ┌─────────┐  ┌─────────┐
         │ Audit   │  │Research │  │ Coding  │
         │ Agent   │  │ Agent   │  │ Agent   │
         └─────────┘  └─────────┘  └─────────┘
```

### Agent Contract Framework

Every agent must declare capabilities and permissions:

```python
@dataclass
class AgentContract:
    agent_id: str
    capabilities: list[Capability]     # What it CAN do
    permissions: list[Permission]       # What it MAY do
    dependencies: list[str]               # What it NEEDS
    risk_level: RiskLevel                # Inherent risk
    evidence_requirements: list[str]     # What it must prove
```

### Policy Engine Checks

Before any agent action:

```python
class PolicyCheck:
    # 1. CAN the agent do this?
    if capability not in agent.contract.capabilities:
        return DENIED("Capability not in contract")
    
    # 2. MAY the agent do this?
    if permission not in agent.contract.permissions:
        return DENIED("Permission not granted")
    
    # 3. SHOULD the agent do this?
    if risk_level >= HIGH:
        return REQUIRES_APPROVAL("User must approve")
    
    # 4. Is this forbidden?
    if action in FORBIDDEN_ACTIONS:
        return DENIED("Action is forbidden")
    
    return ALLOWED()
```

### Forbidden Actions (Never Allowed)

```python
FORBIDDEN_ACTIONS = [
    "modify_constitution",
    "disable_governance", 
    "create_agent_without_approval",
    "bypass_permission_check",
    "access_without_audit",
    "self_modify_capabilities",
]
```

### Audit Trail

Every agent action is logged:

```python
TimelineEvent(
    timestamp=datetime.now(),
    agent_id="coding_agent_1",
    action="file.create",
    target="/workspace/project/phase8.go",
    approved_by="operator",  # Or "auto" for low-risk
    evidence=["git diff", "test results"],
    risk_level=LOW,
)
```

### User Control Points

| Action | User Required? |
|--------|---------------|
| Spawn new agent | YES |
| High-risk task | YES |
| Cross-workspace access | YES |
| Modify agent contract | YES |
| Terminate agent | YES |
| Low-risk task execution | NO (auto-approved) |

---

## Question 4: World Model Reasoning (Phase 10)

### Q: How does ACC transition from conversation-driven to entity-driven reasoning?

### A: The World Model Becomes Primary Context Source

### Before (Conversation-Driven)

```
Chat History
     │
     ▼
"Based on our conversation about Phase 8..."
     │
     ▼
[Limited, Transient, Unstructured]
```

### After (Entity-Driven)

```
World Model
     │
     ├─ Entity Graph
     ├─ Relationships
     ├─ State Projections
     └─ Timeline Events
           │
           ▼
EntityContext
     │
     ├─ Focus Entity (Task "Phase 8")
     ├─ Connected Entities (Files, Goals, Agents)
     ├─ Recent Events (Committed changes)
     └─ Predictions (Blockers, Risks)
           │
           ▼
"Based on the project state, Phase 8 is blocked by..."
```

### Context Engine Assembly

```python
class EntityContext:
    focus_entity: Entity              # The primary entity
    workspace: Workspace              # Parent workspace
    project: Project                  # Parent project
    
    # Relationships
    dependencies: list[Entity]       # BLOCKED_BY
    dependents: list[Entity]        # BLOCKING
    related: list[Entity]            # REFERENCES
    
    # State
    current_status: EntityStatus
    recent_changes: list[TimelineEvent]
    
    # Predictions
    blockers: list[PredictiveAlert]
    risks: list[RiskAssessment]
    
    # Evidence
    evidence: list[str]              # Proof for claims
```

### State Projection Layer

Instead of querying raw entities, views are pre-computed:

```python
# WorkspaceView - All entities in workspace
class WorkspaceProjection:
    entities: list[Entity]
    by_type: dict[EntityType, list[Entity]]
    by_status: dict[Status, list[Entity]]
    
# GoalView - Goal progress
class GoalProjection:
    goal: Goal
    tasks: list[Task]
    completion_percentage: float
    blockers: list[Entity]
    timeline: list[TimelineEvent]
```

### Reasoning Examples

| Query | Conversation-Driven | Entity-Driven |
|-------|-------------------|---------------|
| "What's blocking Phase 8?" | Unclear | Task "Design API" has status BLOCKED |
| "Show me recent work" | Chat messages | Timeline events with evidence |
| "What depends on this?" | Manual search | Graph traversal |
| "What should I do next?" | LLM guess | Predictive analysis |

### World Explorer UI

```
┌─────────────────────────────────────────────────────────────┐
│                    WORLD EXPLORER                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│         ┌──────┐                                           │
│         │Goal  │                                           │
│         │Phase8│                                           │
│         └──┬───┘                                           │
│            │                                                │
│      ┌─────┼─────┐                                        │
│      │     │     │                                        │
│      ▼     ▼     ▼                                        │
│   ┌────┐ ┌────┐ ┌────┐                                   │
│   │Task│ │File│ │Task│                                   │
│   │API │ │.py │ │Test│                                   │
│   └──┬─┘ └────┘ └────┘                                   │
│      │                                                    │
│      ▼                                                    │
│   ┌─────────┐                                             │
│   │ BLOCKED │                                             │
│   │ by: API │                                             │
│   └─────────┘                                             │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Filter: [All] [Goals] [Tasks] [Files] [Agents]            │
│ View: [Graph] [List] [Timeline]                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Question 5: Phase Integration (7→8→9→10)

### Q: How do Phases 7-10 build on each other to achieve the Workspace OS vision?

### A: Progressive Trust Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE EVOLUTION                          │
└─────────────────────────────────────────────────────────────┘

Phase 7: Operational Intelligence (Trust Foundation)
    │
    │ WHY: Before abstraction, we need trust
    │ WHAT: ExecutionOrchestrator, TruthBoundary, Receipts
    │
    ▼
Phase 8: Operator Kernel (Abstraction Foundation)
    │
    │ WHY: Before agents, we need consistent behavior
    │ WHAT: ModelAdapters, ComplianceEngine, ResponseContracts
    │
    ▼
Phase 9: Goals & Multi-Agent (Coordination Foundation)
    │
    │ WHY: Before world-model, we need task management
    │ WHAT: GoalEngine, TaskGraph, AgentCoordinator
    │
    ▼
Phase 10: World Model (Reasoning Foundation)
    │
    │ WHY: After all foundations, we can reason
    │ WHAT: WorldModelService, EntityGraph, ContextEngine
    │
    ▼
WORKSPACE OS
```

### Why This Order?

| Phase | Question | Answer |
|-------|----------|--------|
| **7** | "Can we trust execution?" | Yes, with receipts and validation |
| **8** | "Can we abstract behavior?" | Yes, with Operator Kernel |
| **9** | "Can we coordinate agents?" | Yes, with policies and operator authority |
| **10** | "Can we reason from state?" | Yes, with world model |

### Dependency Graph

```
Phase 7 (Trust)
    │
    ├──► Phase 8 (Operator Kernel)
    │        │
    │        └──► Phase 9 (Goals & Multi-Agent)
    │                    │
    │                    └──► Phase 10 (World Model)
    │
    └──► Phase 5 (Async EventBus)
             │
             └──► All phases require async dispatch
```

### Constitutional Compliance at Each Phase

| Phase | Constitutional Rule | Implementation |
|-------|--------------------|----------------|
| **7** | Execution before explanation | TruthBoundary validates |
| **8** | Behavior belongs to ACC | OperatorKernel owns behavior |
| **9** | Agent never autonomous | PolicyEngine, Operator approval |
| **10** | State drives reasoning | ContextEngine builds entity context |

### Exit Gates Between Phases

```
Phase 7 Exit:
  ✅ Intent → Provider → Receipt pipeline working
  ✅ TruthBoundary catches hallucinations
  ✅ All architectural guarantee tests pass

Phase 8 Exit:
  ✅ Model independence score > 0.95
  ✅ ComplianceEngine catches 100% test hallucinations
  ✅ Same behavior across all model adapters

Phase 9 Exit:
  ✅ Goals persist across restarts
  ✅ Multiple agents can collaborate
  ✅ Operator approval required for high-risk

Phase 10 Exit:
  ✅ ACC reasons from entities, not conversation
  ✅ World Explorer functional
  ✅ Predictive operations identify blockers
```

---

## Summary Table

| Question | Phase | Key Answer |
|----------|-------|------------|
| Model Independence | 8 | Behavior in ACC, reasoning in LLM |
| Goal Persistence | 9 | Goals are entities, stored in SQLite |
| Agent Coordination | 9 | Operator is authority, agents are tools |
| Entity Reasoning | 10 | ContextEngine builds EntityContext |
| Phase Integration | All | Progressive trust architecture |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial Q&A document |
