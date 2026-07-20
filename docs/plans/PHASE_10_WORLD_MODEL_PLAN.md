# Phase 10: Workspace OS Intelligence & World Model Expansion

**Status:** PARTIAL (code-verified 2026-07-20 — core/UI present; predictive/undo not in factory)  
**Priority:** MEDIUM  
**Estimated Effort:** 10-12 weeks  
**Dependencies:** Phase 9 Goals (PARTIAL)  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `VNEXT_STATE_DRIVEN_BLUEPRINT.md`  
**Verification:** `docs/audits/PHASE_PLANS_ARCHIVE_VERIFICATION.md`

---

## Mission

Transform ACC from **Goal Based System** into **Workspace Operating System**.

This is where ACC becomes truly different from ChatGPT, Claude Desktop, or standard agent frameworks.

---

## Core Principle

```
The system no longer reasons primarily from conversations.
It reasons from:

  - Entities
  - Relationships
  - State
  - Events
```

---

## Architecture

```
World Model
     │
     ▼
Entity Graph
     │
     ▼
Relationship Engine
     │
     ▼
State Projection Layer
     │
     ▼
Reasoning Engine
     │
     ▼
Operator
```

---

## Major Subsystems

### 10.1 World Model Service

**New Core Service:** `ai_command_center/world/world_model_service.py`

**Stores:**

```python
# Everything becomes an entity
Entity:
  - id: str
  - entity_type: EntityType
  - name: str
  - properties: dict
  - created_at: datetime
  - updated_at: datetime

EntityType (enum):
  - WORKSPACE
  - PROJECT
  - FILE
  - NOTE
  - TASK
  - GOAL
  - AGENT
  - PROVIDER
  - MODEL
  - KNOWLEDGE_OBJECT
  - RESOURCE
```

**Invariants:**
- `WorldModelService` is the single source of truth
- No duplicate entity storage
- All entities queryable via graph API

### 10.2 Entity Graph

**Graph database style architecture.**

```python
# Example relationships
Workspace "Home"
  ├─ CONTAINS → Project "AI Command Center"
  │    ├─ CONTAINS → File "main.py"
  │    ├─ CONTAINS → Task "Implement Phase 8"
  │    └─ DEPENDS_ON → Project "SDK"
  │
  ├─ CREATED → Goal "Modernize UI"
  │    └─ ASSIGNED_TO → Agent "CodingAgent"
  │
  └─ USES → Provider "Ollama"
```

**Query Capabilities:**
- Traverse by relationship type
- Find connected entities
- Path finding between entities
- Subgraph extraction

### 10.3 Relationship Engine

**Tracks:**

| Relationship | Description |
|--------------|-------------|
| CONTAINS | Parent-child ownership |
| DEPENDS_ON | Blocking dependency |
| REFERENCES | External link |
| DERIVED_FROM | Source relationship |
| ASSIGNED_TO | Task/goal assignment |
| CREATED_BY | Authorship |
| MANAGES | Agent responsibility |

### 10.4 State Projection Layer

**Creates views. Similar to CQRS read models.**

| Projection | Purpose |
|------------|---------|
| WorkspaceView | All entities in a workspace |
| ProjectView | Project tree with dependencies |
| AgentView | Agent's assigned work |
| TimelineView | Chronological event stream |
| GoalView | Goal progress and blockers |

### 10.5 Context Engine

**Instead of:**

```
Conversation Context (limited, transient)
```

**ACC builds:**

```
Entity Context (rich, persistent)
```

**Example:**

```python
EntityContext(
    focus_entity=task("Implement Phase 8"),
    workspace=workspace("AI Command Center"),
    project=project("AI Command Center"),
    dependencies=[
        task("Design Phase 8 API"),
        file("phase8_api.py"),
    ],
    related_goals=[
        goal("Modernize Operator"),
    ],
    recent_activity=[
        event("task.completed: Design API"),
        event("file.created: phase8_api.py"),
    ],
    connected_agents=[
        agent("CodingAgent"),
    ]
)
```

**Massive shift from conversation-driven to entity-driven reasoning.**

### 10.6 Predictive Operations

**The system becomes proactive.**

**Examples:**

```python
# Pattern: Repeated CI failures
PredictiveAlert(
    type="BLOCKER_DETECTED",
    entity=task("Fix CI"),
    prediction="CI failing repeatedly for 5 days",
    recommendation="Investigate root cause before continuing",
    confidence=0.85
)

# Pattern: Goal blocked
PredictiveAlert(
    type="BLOCKER_DETECTED",
    entity=goal("Release v2.0"),
    prediction="Blocked by 3 incomplete tasks",
    recommendation="Focus on task "Fix CI" next",
    confidence=0.92
)
```

### 10.7 Undo / Replay Framework

**Powered by Timeline.**

**Capabilities:**

| Operation | Description |
|-----------|-------------|
| Replay | Reconstruct any past state |
| Rollback | Revert to previous state |
| Recovery | Restore after failure |
| State Reconstruction | Build context from history |

### 10.8 Cross-Workspace Intelligence

**ACC understands deep relationships:**

```
This file
  belongs to
    that project
      which supports
        that goal
          which is blocking
            another goal
```

**This is impossible in chat-centric systems.**

---

## World Explorer UI

**New View:** `ai_command_center/ui/views/world_explorer_view.py`

**Similar to:**
- Obsidian Graph View
- Neo4j Browser
- VS Code Explorer
- Unreal World Outliner

**Displays:**
- Entities (nodes)
- Relationships (edges)
- Dependencies
- Goals
- Agents

**Interactions:**
- Zoom/Pan
- Filter by entity type
- Highlight connections
- Drill into entity details

---

## Success Criteria

- [ ] ACC reasons from world state instead of conversation history
- [ ] Every object is an entity
- [ ] Relationships are queryable
- [ ] Goals, tasks, agents, files, projects are connected
- [ ] Context is generated from the World Model
- [ ] Undo and replay are operational
- [ ] ACC proactively identifies blockers and opportunities
- [ ] Workspace OS behavior driven by entities, events, and state

---

## Files

### Create

```
ai_command_center/world/
├── __init__.py
├── world_model_service.py
├── entity.py
├── entity_type.py
├── entity_graph.py
├── relationship.py
├── relationship_type.py
├── relationship_engine.py
├── state_projections.py
│   ├── __init__.py
│   ├── base_projection.py
│   ├── workspace_projection.py
│   ├── project_projection.py
│   ├── goal_projection.py
│   └── timeline_projection.py
├── context_engine.py
├── predictive_engine.py
├── predictive_alerts.py
├── undo_replay.py
├── timeline.py
└── event_sourcing.py

ai_command_center/ui/views/
├── world_explorer_view.py
├── relationship_visualizer.py
├── dependency_inspector.py
├── world_explorer_sidebar.py
└── entity_detail_panel.py

tests/world/
├── __init__.py
├── test_world_model_service.py
├── test_entity_graph.py
├── test_relationships.py
├── test_state_projections.py
├── test_context_engine.py
├── test_predictive_engine.py
├── test_undo_replay.py
└── test_cross_workspace.py

tests/ui/views/
├── test_world_explorer_view.py
└── test_relationship_visualizer.py
```

### Modify

```
ai_command_center/repositories/
ai_command_center/core/entity/
ai_command_center/core/relationship/
ai_command_center/ui/
```

---

## Exit Criteria

- [ ] World Model Service is single source of truth
- [ ] Entity graph supports all entity types
- [ ] Relationship queries performant
- [ ] State projections update in real-time
- [ ] Context engine generates entity-based context
- [ ] Predictive operations functional
- [ ] Undo/Replay operational
- [ ] World Explorer UI complete
- [ ] Architecture lint clean
- [ ] UCGS PASS

---

## Non-Goals

- Cloud-based entity storage
- Real-time multi-user collaboration on entities
- Graph database migration (SQLite sufficient initially)
- Full-text search integration (Phase 8 Knowledge)

---

## Phase Evolution

```
Phase 7: Operational Intelligence (Trust & Execution)
         │
         ▼
Phase 8: Operator Kernel (Model Independence)
         │
         ▼
Phase 9: Goals & Multi-Agent Coordination (Planning & Persistence)
         │
         ▼
Phase 10: Workspace OS Intelligence (World Model & Reasoning)
```

**This progression is coherent because each phase builds on the guarantees established by the previous one:**
- **Phase 7**: Trust before abstraction
- **Phase 8**: Abstraction before agents
- **Phase 9**: Agents before world-model intelligence
- **Phase 10**: World-model intelligence for true Workspace OS

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial plan |
