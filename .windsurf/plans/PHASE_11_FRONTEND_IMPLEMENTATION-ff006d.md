# ACC Phase 11 Frontend Implementation Plan

A state-first, UI-Constitution-compliant implementation plan that exposes ACC's existing backend projections through renderer-only views, starting with the Command Center Dashboard and Top Bar.

---

## Authority & Governance

- **Backend authority:** `PROJECT_CONSTITUTION_V4.md` (Invariant 1: UI → AppState → EventBus → Services → Repositories → Storage).
- **Frontend authority:** `docs/UI_CONSTITUTION.md` (this plan references the UI Constitution created in this step).
- **Architecture:** `ARCHITECTURE.md` and `ARCHITECTURE_ENFORCEMENT.md` — UI reads `AppState` and publishes `EventBus` events; no direct repository/service access.
- **No-regression covenant:** `docs/architecture/ACC_UI_REFURBISHMENT.md` — new UI extends existing infrastructure; `TimelineRenderer`, `GraphCanvas`, `InspectorHost`, `WorkflowGraphView`, etc., remain reusable primitives.

---

## Core Principles

1. **No new AppState fields.** Every phase uses existing projections. If a view needs composition, it is done at the UI layer (in `StateApplierMixin` or view components).
2. **Renderer-only UI.** Views read `AppState`, render, and publish `EventBus` events through `UIController`. They do not call repositories, services, or databases.
3. **Mission Control identity.** Dark, dense, operational. No chat-app or generic admin aesthetics.
4. **Hero-first, evidence-first.** Every primary workspace has a Hero Section and shows status, receipts, sources, and validation.

---

## Existing AppState Projections Used

| View | AppState Source | Key Fields |
|---|---|---|
| **Command Center Dashboard** | `brain_state`, `execution_library`, `permission_snapshot`, `agent_pipeline`, `world_model`, `provider_registry` | `brain_state.recent_goals`, `execution_library.active_plan`, `permission_snapshot.pending`, `agent_pipeline.active_run_ids`, `world_model.node_count` / `relationship_count`, `provider_registry.providers` |
| **Top Bar** | `brain_state`, `permission_snapshot`, `agent_pipeline`, `model_selection` | `brain_state.kernel_state`, `brain_state.recent_goals`, `permission_snapshot.pending`, `agent_pipeline.active_runs`, `model_selection` |
| **World Model Workspace** | `world_model` | `nodes`, `edges`, `edges_for_selected`, `mutation_log`, `goals`, `selected_node_id`, `node_count`, `mutation_count` |
| **Execution Center** | `execution_library`, `execution_timeline`, `execution_context`, `orchestration_run` | `active_plan` (steps, status, error), `run_history`, `execution_timeline`, `execution_context.receipt_id`, `orchestration_run.run_history` (truth, receipt) |
| **Agent Monitor** | `agent_pipeline` | `runs`, `active_run_id`, `active_run_ids`, `pipeline_id`, `pipeline_stage`, `planned_tools`, `total_spawned` |
| **Approval Center** | `permission_snapshot`, `brain_recent_runtime_actions` | `permission_snapshot.pending`, `resolved`, `total_*`; `brain_recent_runtime_actions` for history |
| **Goal Dashboard** | `brain_state`, `planner_last_plan` | `brain_state.recent_goals`, `brain_state.last_plan`, `planner_last_plan` |

---

## Phase 11A — Command Center Dashboard + Top Bar

**Objective:** Create the default operational homepage and global status bar.

**UI Constitution Articles:** 8, 9, 17.

### Command Center Dashboard Components

| Component | Article | Content |
|---|---|---|
| Hero Section | 7, 8 | Workspace name "Command Center", current state, active goal, critical summary, immediate action |
| Operations Grid | 8, 10 | Cards for Executions, Agents, Approvals, Providers — each with header, metric, status, timestamp, action |
| System Awareness | 8 | World Model summary, knowledge stats, recent changes |

### Data Sources

- Active Goal: `brain_state.recent_goals` (first ACTIVE goal)
- Running Execution: `execution_library.active_plan`
- Pending Approvals: `permission_snapshot.pending`
- Active Agents: `agent_pipeline.active_runs`
- World Model: `world_model.node_count`, `world_model.relationship_count` (or `edges` length), `world_model.active_goals`
- Provider Health: `provider_registry.providers` / `provider_health_map`

### Top Bar

- Active Goal pill (click → Goal Dashboard)
- Kernel status badge (color-coded)
- Active agents count badge
- Pending approvals count badge (click → Approval Center)
- Current model/provider badge
- Time

### Files

- `ai_command_center/ui/views/command_center_view.py` (new)
- `ai_command_center/ui/components/top_bar.py` (modify)
- `ai_command_center/ui/shell/state_applier.py` (drive new view)
- `ai_command_center/ui/shell/view_manager.py` (register view)
- `ai_command_center/ui/components/sidebar.py` (add nav item)

### Acceptance Criteria

- [ ] Command Center is the default view on launch.
- [ ] Hero Section displays active goal, status, and one immediate action.
- [ ] Operations Grid cards show header, metric, status, timestamp, action.
- [ ] Top Bar displays all six required elements from Article 17.
- [ ] Clicking a Top Bar badge navigates to the correct workspace.

---

## Phase 11B — World Model Workspace

**Objective:** Make the knowledge graph a first-class operating surface.

**UI Constitution Articles:** 5 (Teal), 12.

### Required Panels (Article 12)

1. **Knowledge Graph** — force-directed or canvas graph of `world_model.nodes` and `world_model.edges`.
2. **Entity Explorer** — list/filter nodes by type.
3. **Relationship Explorer** — incoming/outgoing edges for `world_model.selected_node_id`.
4. **Mutation Journal** — last 200 entries from `world_model.mutation_log`.
5. **Selection Inspector** — attributes of selected node.

### Hero Section

- Workspace Name: "World Model"
- Current State: "`<node_count>` entities, `<edge_count>` relationships"
- Primary Metric: active goals count
- Immediate Action: "New Entity" (publishes `WORLD_MODEL_MUTATION_APPLIED`)

### Files

- `ai_command_center/ui/views/world_explorer_view.py` (enhance)
- `ai_command_center/ui/components/graph_canvas.py` (reuse)
- `ai_command_center/ui/views/world_model/` panels (new if needed)

### Acceptance Criteria

- [ ] All nodes and edges are visible in the graph.
- [ ] Clicking a node selects it and updates Relationship Explorer + Selection Inspector.
- [ ] Mutation Journal shows the last 200 mutations with expandable details.
- [ ] Graph uses Teal color identity for World Model nodes.

---

## Phase 11C — Execution Center

**Objective:** Give operators complete runtime visibility and evidence.

**UI Constitution Articles:** 5 (Blue), 13.

### Required Panels (Article 13)

1. **Execution List** — `execution_library.run_history` filtered by status.
2. **Execution Timeline** — `execution_timeline` and `execution_library.active_plan.steps`.
3. **Execution Detail** — `execution_context` + `orchestration_run` for the selected run.
4. **Receipt Viewer** — `orchestration_run.run_history[].receipt_id`.
5. **Truth Validation** — `orchestration_run.run_history[].truth_valid` / `truth_detail`.

### Hero Section

- Workspace Name: "Execution Center"
- Current State: "`<running>` running, `<total>` total"
- Primary Metric: active run ID and current step
- Immediate Action: "View All" / filter

### Files

- `ai_command_center/ui/views/executions_view.py` (enhance)
- `ai_command_center/ui/views/execution_detail.py` (new)
- `ai_command_center/ui/components/execution_timeline.py` (reuse/extend)

### Acceptance Criteria

- [ ] Execution list shows run ID, goal, status badge, duration.
- [ ] Timeline shows steps with status (running, completed, failed).
- [ ] Receipt Viewer shows receipt ID, provider, facts, success.
- [ ] Truth Validation shows `truth_valid` and `truth_detail`.

---

## Phase 11D — Agent Monitor

**Objective:** Expose multi-agent runtime and pipeline progress.

**UI Constitution Articles:** 5 (Purple), 14.

### Required Panels (Article 14)

1. **Active Agents** — `agent_pipeline.runs` / `agent_pipeline.active_runs`.
2. **Agent State** — per-agent `task`, `state`, `steps`, `error`.
3. **Pipeline Progress** — `agent_pipeline.pipeline_stage` and `agent_pipeline.planned_tools`.
4. **Task Assignment** — mapping of agent to current task.
5. **Execution History** — completed agent runs.

### Hero Section

- Workspace Name: "Agent Monitor"
- Current State: "`<active>` active agents"
- Primary Metric: pipeline stage (e.g., "Research Phase")
- Immediate Action: "Cancel" (publishes `AGENT_CANCEL_REQUEST`)

### Files

- `ai_command_center/ui/views/agent_monitor_view.py` (new)
- `ai_command_center/ui/components/agent_card.py` (new)
- `ai_command_center/ui/components/pipeline_progress.py` (new)

### Acceptance Criteria

- [ ] Active agents list shows role, task, state, progress.
- [ ] Pipeline Progress shows stage and planned tools count.
- [ ] Cancel button publishes `AGENT_CANCEL_REQUEST`.

---

## Phase 11E — Approval Center

**Objective:** Make approvals a permanent, visible workspace.

**UI Constitution Articles:** 5 (Orange), 15.

### Required Panels (Article 15)

1. **Pending Queue** — `permission_snapshot.pending`.
2. **Decision History** — `permission_snapshot.resolved`.
3. **Risk Classification** — risk level from `ExecutionStepSnapshot.risk` or `permission_snapshot` payload.
4. **Approval Statistics** — `total_requested`, `total_granted`, `total_denied`.

### Hero Section

- Workspace Name: "Approval Center"
- Current State: "`<pending>` pending"
- Primary Metric: last decision outcome
- Immediate Action: "Review Next"

### Files

- `ai_command_center/ui/views/approval_center_view.py` (new)
- `ai_command_center/ui/components/approval_item.py` (new)
- `ai_command_center/ui/controller.py` (publish `PERMISSION_CHECK_RESULT`)

### Acceptance Criteria

- [ ] Pending Queue shows description, risk, timestamp, actor.
- [ ] Approve/Deny buttons publish `PERMISSION_CHECK_RESULT`.
- [ ] Decision History shows outcome, timestamp, summary, correlation ID.
- [ ] Empty state explains why no approvals are pending and suggests next action.

---

## Phase 11F — Goal Dashboard

**Objective:** Make goals, plans, and lifecycle visible and actionable.

**UI Constitution Articles:** 5 (Amber), 16.

### Required Panels (Article 16)

1. **Goal List** — `brain_state.recent_goals` filtered by status.
2. **Goal Detail** — description, metadata, errors, priority.
3. **Plan Preview** — `planner_last_plan` or `brain_state.last_plan`.
4. **Goal Progress** — status and completion percentage.
5. **Goal History** — status changes from `brain_state.recent_goals`.

### Hero Section

- Workspace Name: "Goal Dashboard"
- Current State: "`<active>` active goals"
- Primary Metric: highest-priority active goal title
- Immediate Action: "New Goal"

### Files

- `ai_command_center/ui/views/goals_view.py` (new)
- `ai_command_center/ui/components/goal_item.py` (new)
- `ai_command_center/ui/components/plan_preview.py` (new)

### Acceptance Criteria

- [ ] Goal list filters by status (Active, Queued, Paused, Completed, Failed, Cancelled).
- [ ] Each row shows title, priority badge, status badge, date.
- [ ] Plan Preview displays `planner_last_plan` steps.
- [ ] Actions publish `GOAL_SUBMIT_REQUEST`, `GOAL_ACTIVATED`, `GOAL_PAUSED`, `GOAL_CANCELLED`.

---

## Verification

After each phase, run:

```bash
python3 -m pytest -m "not slow"
python3 -m ruff check ai_command_center
python3 scripts/verify_constitution.py
```

A new `scripts/verify_ui_constitution.py` should be created during Phase 11A to check:

- Hero Sections exist on all primary workspaces.
- Cards have header, metric, status, timestamp, action.
- Status badges include both color and text.
- No UI component mutates repositories.
- All mandatory workspaces are in navigation.
- Empty states are informative.

---

## Definition of Done

Phase 11 is complete when:

1. ✅ All mandatory workspaces exist and are accessible from navigation.
2. ✅ Each workspace has a compliant Hero Section.
3. ✅ All cards follow Card Standards.
4. ✅ Status badges use both color and text.
5. ✅ Top Bar displays all required elements.
6. ✅ UI reads only from `AppState` and publishes `EventBus` events.
7. ✅ `scripts/verify_constitution.py` passes.
8. ✅ `python3 -m ruff check ai_command_center` passes.
9. ✅ Operators can observe every major backend subsystem without reading logs.

---

## Implementation Order & Estimated Effort

| Phase | Title | Effort |
|---|---|---|
| 11A | Command Center Dashboard + Top Bar | 2 days |
| 11B | World Model Workspace | 3 days |
| 11C | Execution Center | 2 days |
| 11D | Agent Monitor | 2 days |
| 11E | Approval Center | 1.5 days |
| 11F | Goal Dashboard | 2 days |

**Total:** ~12.5 working days.

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| AppState field names differ from plan | Verify exact names from `core/app_state.py` before each phase. |
| Graph performance with many nodes | Use level-of-detail or limit initial visible nodes. |
| Goal lifecycle controls | Phase 11F is read-only if `GoalEngine` persistence projection is not added. |
| Execution truth/receipt split | Composite from `execution_library`, `execution_context`, and `orchestration_run` in `StateApplierMixin`. |
| Sidebar overflow | Group workspaces into collapsible sections (Ops, Monitor, Library). |

---

## Open Questions

1. Should the Command Center Dashboard replace `HomeView` as the default view, or coexist?
2. For Phase 11F, do you want read-only goal visibility first, or should we add a `GoalEngine` → `AppState` projection before UI work?
