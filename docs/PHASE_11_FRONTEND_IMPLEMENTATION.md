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

**Status:** Complete.

**Objective:** Create the default operational homepage and global status bar.

**UI Constitution Articles:** 8, 9, 17.

### Command Center Dashboard Components

| Component | Article | Content |
|---|---|---|
| Hero Section | 7, 8 | Workspace name **Command Center** (canonical), current state, active goal, critical summary, immediate action |
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

- [x] Command Center is the default view on launch.
- [x] Hero Section displays active goal, status, and one immediate action.
- [x] Operations Grid cards show header, metric, status text + color, timestamp, action.
- [x] Top Bar displays all six required elements from Article 17.
- [x] Clicking a Top Bar badge navigates to the correct workspace.
- [x] Surface states: Loading / Empty / Error / Data (Article 18 empty copy).

---

## Phase 11B — World Model Workspace

**Status:** Complete.

**Objective:** Make the knowledge graph a first-class operating surface.

**UI Constitution Articles:** 5 (`WORLD_TEAL`), 12.

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
- Immediate Action: "New Entity" (publishes `ENTITY_CREATE_REQUEST`; never `WORLD_MODEL_MUTATION_APPLIED`)

### Files

- `ai_command_center/ui/views/world_explorer_view.py` (orchestration shell)
- `ai_command_center/ui/views/world_model/knowledge_graph_panel.py`
- `ai_command_center/ui/views/world_model/entity_explorer_panel.py`
- `ai_command_center/ui/views/world_model/selection_inspector_panel.py`
- `ai_command_center/ui/views/world_model/relationship_explorer_panel.py`
- `ai_command_center/ui/views/world_model/mutation_journal_panel.py`

### Acceptance Criteria

- [x] All nodes and edges are visible in the graph.
- [x] Clicking a node selects it and updates Relationship Explorer + Selection Inspector.
- [x] Mutation Journal shows the last 200 mutations with expandable details.
- [x] Graph uses Teal color identity for World Model nodes.
- [x] Reads `AppState.world_model` only (no `WorldModelState` listeners).
- [x] Hero publishes `ENTITY_CREATE_REQUEST`.
- [x] `scripts/verify_ui_constitution.py` includes Phase 11B checks.

---

## Phase 11C — Execution Center

**Status:** Complete.

**Objective:** Give operators complete runtime visibility and evidence.

**UI Constitution Articles:** 5 (Blue / `EXECUTION_BLUE`), 13.

### Required Panels (Article 13)

1. **Execution List** — `execution_library.run_history` filtered by status.
2. **Execution Timeline** — `execution_timeline` / scrubber and `execution_library.active_plan.steps`.
3. **Execution Detail** — `execution_library.active_plan` + `execution_context`.
4. **Receipt Viewer** — visualization of `orchestration_run` only (no separate receipt model).
5. **Truth Validation** — `orchestration_run.truth_valid` / `truth_detail` (separate from receipts).

### Hero Section

- Workspace Name: "Execution Center"
- Metrics: active, total, failed, success rate
- Immediate Action: "View Active Execution" / "Open Latest Execution"

### Files

- `ai_command_center/ui/views/executions_view.py` (orchestration shell)
- `ai_command_center/ui/views/execution_center/execution_list_panel.py`
- `ai_command_center/ui/views/execution_center/execution_timeline_panel.py`
- `ai_command_center/ui/views/execution_center/execution_detail_panel.py`
- `ai_command_center/ui/views/execution_center/receipt_viewer_panel.py`
- `ai_command_center/ui/views/execution_center/truth_validation_panel.py`

### Acceptance Criteria

- [x] Execution list shows run ID, goal, status badge, duration (failures-first sort).
- [x] Timeline shows steps with status (running, completed, failed, waiting).
- [x] Receipt Viewer shows receipt ID, response source, outcome, evidence from `orchestration_run`.
- [x] Truth Validation shows valid/partial/failed via centralized status tokens.
- [x] Uses existing execution projections only; no new AppState/services/repos.
- [x] `EXECUTION_BLUE` token + `verify_ui_constitution.py` Phase 11C checks.
- [x] Hero action disabled with updated label when no execution target exists.
- [x] Surface states: Loading / Empty / Error / Data (Article 18 empty copy).

---

## Phase 11D — Agent Monitor

**Objective:** Expose multi-agent runtime and pipeline progress.

**UI Constitution Articles:** 5 (Purple / `AGENT_PURPLE`), 14.

**Status:** Complete (pipeline-first layout + failure visibility).

### Required Panels (Article 14)

1. **Pipeline Progress** (primary visual) — `pipeline_stage`, `planned_tools`, derived completed/remaining.
2. **Active Agents** — `agent_pipeline.runs` (Running → Waiting → Failed → Completed).
3. **Agent State** — state, error, last transition, runtime metadata.
4. **Task Assignment** — read-only task/role/request/pipeline mapping.
5. **Execution History** — all projected runs only (no history service).

### Hero Section

- Workspace Name: "Agent Monitor"
- Metrics: Active Agents · Pipeline Stage · Planned Tools · Running Tasks · Failure count
- Immediate Action: contextual **Cancel Active Pipeline** / **Cancel Selected Agent Run**
  (publishes `AGENT_CANCEL_REQUEST`; disabled when no active run)

### Files

- `ai_command_center/ui/views/agents_view.py` (shell, route `agents`)
- `ai_command_center/ui/views/agent_monitor/` panels
- `tests/ui/test_agent_monitor_projection.py`
- `scripts/verify_ui_constitution.py` Phase 11D checks

### Acceptance Criteria

- [x] Hero + five Article 14 panels project `AppState.agent_pipeline` only.
- [x] Pipeline Progress dominates layout; failures visible in Hero + history.
- [x] Contextual Cancel publishes `AGENT_CANCEL_REQUEST`.
- [x] `AGENT_PURPLE` documented; no new AppState/services/repositories.

---

## Phase 11E — Approval Center

**Objective:** Make approvals a permanent, visible workspace.

**UI Constitution Articles:** 5 (Orange / `APPROVAL_ORANGE`), 15.

**Status:** Complete (Pending Queue primary; explicit risk rationale).

### Required Panels (Article 15)

1. **Pending Queue** (primary) — `permission_snapshot.pending` + Approve/Deny.
2. **Risk Classification** — composed (execution step → capability map → unknown) with reason/source.
3. **Decision History** — `permission_snapshot.resolved` only (no invented timestamps).
4. **Approval Statistics** — `total_requested` / `granted` / `denied` + pending count.

### Hero Section

- Workspace Name: "Approval Center"
- Metrics: Pending · Granted · Denied · Last Decision (`resolved[0]` or "No decisions recorded")
- Immediate Action: **Review Next** (focus only; never approve/deny)

### Files

- `ai_command_center/ui/views/approvals_view.py` (shell, route `approvals`)
- `ai_command_center/ui/views/approval_center/` panels
- `tests/ui/test_approval_center_projection.py`
- `scripts/verify_ui_constitution.py` Phase 11E checks

### Acceptance Criteria

- [x] Pending Queue dominates layout; empty state explains next step.
- [x] Approve/Deny publish `PERMISSION_CHECK_RESULT`.
- [x] Risk Classification shows tier + reason + source (unknown explicit).
- [x] Last Decision from resolved ordering only; `APPROVAL_ORANGE` documented.

---

## Phase 11F — Goal Dashboard

**Status:** Complete.

**Objective:** Make goals, plans, and lifecycle visible and actionable.

**UI Constitution Articles:** 5 (`GOAL_AMBER`), 16.

### Required Panels (Article 16)

1. **Goal List** — `brain_state.recent_goals` filtered by status.
2. **Goal Detail** — description, metadata, errors, priority.
3. **Plan Preview** — `brain_state.last_plan` with `planner_last_plan` fallback.
4. **Goal Progress** — derived from projected plan step statuses.
5. **Goal History** — projected goals from `brain_state.recent_goals`.

### Hero Section

- Workspace Name: "Goal Dashboard"
- Metrics: Active · Queued · Paused · Failed
- Primary Metric: highest-priority active goal title
- Immediate Action: **New Goal** → `publish_goal_submit_request` → `GOAL_SUBMIT_REQUEST`
- Does **not** publish lifecycle facts (`GOAL_ACTIVATED` / `GOAL_PAUSED` / `GOAL_CANCELLED`)

### Files

- `ai_command_center/ui/views/goal_view.py` (orchestration shell, route `goals`)
- `ai_command_center/ui/views/goal_dashboard/goal_list_panel.py`
- `ai_command_center/ui/views/goal_dashboard/goal_detail_panel.py`
- `ai_command_center/ui/views/goal_dashboard/plan_preview_panel.py`
- `ai_command_center/ui/views/goal_dashboard/goal_progress_panel.py`
- `ai_command_center/ui/views/goal_dashboard/goal_history_panel.py`
- `tests/ui/test_goal_dashboard_projection.py`
- `scripts/verify_ui_constitution.py` Phase 11F checks

### Acceptance Criteria

- [x] Goal list filters by status (Active, Queued, Paused, Completed, Failed, Cancelled).
- [x] Each row shows title, priority badge, status badge (color + text).
- [x] Plan Preview displays `brain_state.last_plan` / `planner_last_plan` steps.
- [x] New Goal publishes `GOAL_SUBMIT_REQUEST` only (no lifecycle fact publishes from UI).
- [x] Reads `AppState.brain_state` (+ optional `planner_last_plan`); no GoalRepository/GoalEngine/services.
- [x] `GOAL_AMBER` documented in `docs/UI_CONSTITUTION.md` and used by shell + panels.
- [x] Sidebar label is "Goal Dashboard"; surface states Loading / Empty / Error / Data.

---

## Verification

After each phase, run:

```bash
python3 -m pytest -m "not slow"
python3 -m ruff check ai_command_center
python3 scripts/verify_constitution.py
python3 scripts/verify_ui_constitution.py
```

`scripts/verify_ui_constitution.py` checks:

- Hero Sections exist on all primary workspaces (11A–11F).
- Cards have header, metric, status, timestamp, action.
- Status badges include both color and text.
- No UI component mutates repositories.
- All mandatory workspaces are in navigation (no orphan routes).
- Empty states are informative (Article 18).
- Phase 11F Goal Dashboard contracts (`GOAL_AMBER`, five panels, submit wiring).

---

## Definition of Done

Phase 11 is **COMPLETE** when:

1. ✅ All mandatory workspaces exist and are accessible from navigation.
2. ✅ Each workspace has a compliant Hero Section.
3. ✅ All cards follow Card Standards.
4. ✅ Status badges use both color and text (canonical `status_tokens.py`).
5. ✅ Top Bar displays all required elements.
6. ✅ UI reads only from `AppState` and publishes `EventBus` events.
7. ✅ `scripts/verify_constitution.py` passes.
8. ✅ `scripts/verify_ui_constitution.py` passes (including Phase 11F).
9. ✅ `python3 -m ruff check ai_command_center` passes.
10. ✅ Operators can observe every major backend subsystem without reading logs.
11. ✅ Goal Dashboard tested via `tests/ui/test_goal_dashboard_projection.py`.

---

## Implementation Order

| Phase | Title | Status |
|---|---|---|
| 11A | Command Center Dashboard + Top Bar | Complete |
| 11B | World Model Workspace | Complete |
| 11C | Execution Center | Complete |
| 11D | Agent Monitor | Complete |
| 11E | Approval Center | Complete |
| 11F | Goal Dashboard | Complete |

---

## Risk Mitigation (closed)

| Risk | Resolution |
|---|---|
| AppState field names differ from plan | Verified against `core/app_state.py` / domain snapshots. |
| Graph performance with many nodes | LOD / initial visible-node limits in World Model panels. |
| Goal lifecycle controls | UI submits intent only (`GOAL_SUBMIT_REQUEST`); lifecycle facts remain service-owned. |
| Execution truth/receipt split | Composed from `execution_library`, `execution_context`, and `orchestration_run`. |
| Sidebar overflow | Grouped workspaces; orphan gallery route removed from registry. |
