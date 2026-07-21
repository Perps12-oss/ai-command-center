# Phase B UI Implementation Roadmap — Evolution Plan

**Status:** ACTIVE implementation roadmap (Devin UI)  
**Baseline:** `origin/main` only  
**Handover:** [`docs/agents/DEVIN_UI_HANDOVER.md`](../agents/DEVIN_UI_HANDOVER.md)  
**Audit gate:** [`docs/agents/CURSOR_AUDIT_GATE.md`](../agents/CURSOR_AUDIT_GATE.md)  
**Authority:** ADR-006 (ExecutionAuthority canonical); [`REPOSITORY_TRUTH_CANON.md`](../audits/REPOSITORY_TRUTH_CANON.md)

This is the reconciled **evolution** version of the Phase B UI roadmap (not a rewrite plan). Foundation, workspaces, and inspector/palette primitives already exist on `main`. Remaining work is **incremental evolution**.

> **Do not branch from `phase-11a-command-center`.** That branch is superseded. Inventory SoT is `origin/main`.

---

## 1. Existing Functionality Already Implemented

### In `origin/main` already

| Capability | What exists | Key files |
|------------|-------------|-----------|
| **Inspector framework** | `InspectorHost` + typed `BaseInspector` subclasses for `message`, `artifact`, `provider`, `decision`, `execution`, `payload`, `workflow_node`. `InspectorDock` exists. | `ui/components/inspector/inspector_host.py`, `ui/components/inspector/*.py`, `ui/components/docks/inspector_dock.py` |
| **Inspectable refs** | `InspectableRef` domain object and `ui/components/inspector/inspect_gestures.py` gesture binding. | `domain/inspectable.py` |
| **Command palette** | `CommandPalette` toplevel triggered by `Ctrl+K`; static list plus dynamic `workspace_os` entity commands. | `ui/design_system/command.py`, `ui/shell/application_shell.py` |
| **Top bar** | Glass `TopBar` with app title, active-goal button, kernel/agents/approvals/model/provider pills, time, settings, close. | `ui/components/top_bar.py` |
| **Sidebar / view registry** | `Sidebar` lists all views; `ViewManager` registers `home`, `chat`, `executions`, `timeline`, `workflow`, `automation`, `world_explorer`, `relationships`, `dependencies`, `providers`, `capabilities`, `artifacts`, `notes`, `memory`, `system`, `plugins`, `settings`. | `ui/components/sidebar.py`, `ui/shell/view_manager.py` |
| **Chat workspace** | Full streaming chat with message blocks, artifact/decision cards, `InspectorDock`, `ExecutionInspector`, chat search, sessions. | `ui/views/chat/chat_view.py`, `ui/views/chat/*.py` |
| **World Model Explorer** | Node browser with filters, type icons/colors, detail panel, `WORLD_MODEL_NODE_SELECTED` events. | `ui/views/world_explorer_view.py` |
| **Relationship graph** | Radial graph canvas + scrollable edge list for selected node, publishes `WORLD_MODEL_NODE_SELECTED`. | `ui/views/relationship_view.py`, `ui/components/graph_canvas.py` |
| **Execution views** | `ExecutionsView`, `ExecutionTimelineView`, `ExecutionDetailView`, timeline scrubber, execution event lists. | `ui/views/executions_view.py`, `ui/views/execution_timeline_view.py`, `ui/views/execution_detail_view.py`, `ui/components/docks/execution_timeline_dock.py` |
| **Automation / workflow** | `AutomationWorkspaceView`, `WorkflowGraphView`, node library palette, workflow toolbar. | `ui/views/automation_workspace_view.py`, `ui/views/workflow_graph_view.py`, `ui/components/node_library_palette.py` |
| **Memory / Notes / Settings / System / Plugins** | Working list views with `apply_state` callbacks. | `ui/views/memory_view.py`, `ui/views/notes_view.py`, `ui/views/settings_view.py`, `ui/views/system_view.py`, `ui/views/plugins_view.py` |
| **AppState projections** | `brain_state`, `world_model`, `agent_pipeline`, `execution_library`, `execution_timeline`, `execution_inspector`, `permission_snapshot`, `provider_registry`, `orchestration_run`, `workflow_library`, `automation_workspace`, `model_artifact`, `notes_memory`, `workspace_entity`, `inspector`, `model_selection`. | `core/app_state.py` |
| **EventBus topics** | `UI_NAVIGATE`, `UI_PALETTE_OPEN/CLOSE`, `UI_INSPECT_SELECT/CLEAR/NAVIGATE`, `UI_EXECUTION_TIMELINE_SCRUB`, `UI_WORKFLOW_NODE_SELECT/MOVE/RUN`, `UI_AUTOMATION_*`, `WORLD_MODEL_NODE_SELECTED/DESELECTED`, memory/goal/agent/execution topics. | `core/events/topics.py` |
| **UI Controller** | Publishes navigate, inspect, palette, execution, workflow, automation, memory, note, settings, chat intents. | `ui/controller.py` |
| **State applier** | Applies `AppState` to chat, home, memory, notes, plugins, system, workspace, executions, providers, capabilities, artifacts, workflow graph, automation, world/relationship/dependency views. | `ui/shell/state_applier.py` |

### Added in `phase-11a-command-center` (HEAD) beyond `origin/main`

| Capability | What exists | Key files |
|------------|-------------|-----------|
| **Command Center dashboard** | New `CommandCenterView` with hero, operations grid, system awareness. | `ui/views/command_center_view.py` |
| **Top Bar live wiring** | `TopBar` reads `brain_state`, `permission_snapshot`, `agent_pipeline`, `model_selection`. | `ui/components/top_bar.py`, `ui/shell/state_applier.py` |
| **New primary workspaces** | `GoalView`, `AgentsView`, `ApprovalsView` registered and wired. | `ui/views/goal_view.py`, `ui/views/agents_view.py`, `ui/views/approvals_view.py`, `ui/shell/view_manager.py` |
| **Consolidated snapshots** | `NotesMemorySnapshot`, `WorkspaceEntitySnapshot`, `ModelArtifactSnapshot` and reducers. | `domain/notes_memory_snapshot.py`, `domain/workspace_entity_snapshot.py`, `domain/model_artifact_snapshot.py`, `core/app_state.py` |
| **UI Constitution & verification** | `docs/UI_CONSTITUTION.md`, `scripts/verify_ui_constitution.py`. | `docs/UI_CONSTITUTION.md`, `scripts/verify_ui_constitution.py` |
| **Command Center default** | `app.py` defaults to `command_center` when `workspace_os_enabled`. | `ui/app.py` |

---

## 2. Missing Functionality

These capabilities are **not present** in `origin/main` or `HEAD` and are the real scope of the evolution plan.

| # | Missing capability | Why it matters |
|---|-------------------|----------------|
| 1 | **Global Context Bar** | No shell-wide context widget; chat has local `chat_context_sources` / `chat_token_estimate` but nothing global. |
| 2 | **OS Palette provider system** | `CommandPalette` is hard-coded in `application_shell.py`; no provider registration, context sections, or dynamic command scoping. |
| 3 | **Navigation shell grouping** | `Sidebar` is a flat list of 21 items; no collapsible groups (Ops, Monitor, Library, etc.). |
| 4 | **Memory Workspace** | `MemoryView` is a simple list/delete view; missing search, detail pane, injection indicator, inspector. |
| 5 | **Brain Inspector workspace** | No dedicated `BrainView`; brain data is only consumed by `TopBar` and `CommandCenterView`. |
| 6 | **Goal Workspace** | `GoalView` is a basic goals list + last plan; missing goal tree, task detail, success criteria, inspector. |
| 7 | **Agent Operations Center** | `AgentsView` shows pipeline + run labels; missing run timelines, per-agent detail, inspector. |
| 8 | **Evidence Workspace** | No `EvidenceView` for claims, truth validation, facts, receipts. |
| 9 | **Mission Control Operations** | No `OperationsView` for the live `Planner → Router → Executor → Verifier → Receipt` pipeline. |
| 10 | **Relationship Graph Workspace** | `RelationshipView` is node-centric; no full-graph workspace with search/filters. |
| 11 | **Insights Placeholder** | No `insights` view, state, or sidebar entry. |
| 12 | **Extended inspector kinds** | `InspectorHost` only registers `message`, `artifact`, `provider`, `decision`. Missing `goal`, `task`, `memory`, `agent`, `note`, `world_node`, `execution_event`. |
| 13 | **UI-level EventBus topics** | Missing `UI_CONTEXT_*`, `UI_MEMORY_*`, `UI_GOAL_*`, `UI_AGENT_*`, `UI_WORLD_*`, `UI_EVIDENCE_*`, `UI_OPERATION_*`, `UI_GRAPH_*`, `UI_INSIGHTS_*`. |
| 14 | **Composite state projections** | No `global_context`, `evidence_state`, `operations_state`, or `insights_state` projections (can reuse existing snapshots or add new reducers). |

---

## 3. Files That Can Be Reused

These files are already implemented and should be **extended, not rewritten**.

| File | Reuse as |
|------|----------|
| `ui/components/inspector/inspector_host.py` | Add new kind registrations and breadcrumb/navigate button. |
| `ui/components/inspector/base_inspector.py` | Base class for new inspectors. |
| `ui/components/inspector/message_inspector.py` | Existing; keep. |
| `ui/components/inspector/artifact_inspector.py` | Existing; keep. |
| `ui/components/inspector/decision_inspector.py` | Existing; keep. |
| `ui/components/inspector/provider_inspector.py` | Existing; keep. |
| `ui/components/inspector/execution_inspector.py` | Existing; keep; tab modules it imports should be relocated, not deleted. |
| `ui/components/docks/inspector_dock.py` | Embed in new workspaces. |
| `ui/components/graph_canvas.py` | Reuse for world-model graph or create `WorldGraphCanvas` adapter. |
| `ui/views/world_explorer_view.py` | Add graph canvas and inspector docking. |
| `ui/views/relationship_view.py` | Integrate into graph workspace or world explorer. |
| `ui/views/command_center_view.py` | Absorb any remaining `HomeView` widgets. |
| `ui/views/goal_view.py` | Evolve into full goal workspace. |
| `ui/views/agents_view.py` | Evolve into agent operations center. |
| `ui/views/approvals_view.py` | Keep as approval center; enhance if needed. |
| `ui/views/memory_view.py` | Evolve into memory workspace. |
| `ui/views/executions_view.py` | Reuse for execution/evidence context. |
| `ui/views/execution_timeline_view.py` | Reuse for mission control timeline. |
| `ui/components/top_bar.py` | Live AppState wiring already present; add context bar below it. |
| `ui/components/sidebar.py` | Keep row rendering; add grouping component. |
| `ui/design_system/command.py` | Refactor `CommandPalette.show()` to accept provider sections. |
| `ui/shell/application_shell.py` | Add context bar and palette provider wiring. |
| `ui/shell/view_manager.py` | Register new views only. |
| `ui/shell/state_applier.py` | Add `apply_state` calls for new views/context bar. |
| `ui/controller.py` | Add intent publishers for new UI topics. |
| `core/events/topics.py` | Append new UI topics. |
| `core/app_state.py` | Add reducer-based composite snapshots. |
| `core/state/inspector_state.py` | Extend `kind` → view navigation map. |
| `domain/inspectable.py` | Add factory helpers for new kinds. |
| `domain/brain_state_snapshot.py` | Source for Brain/Goal workspaces. |
| `domain/world_model_snapshot.py` | Source for World/Graph workspaces. |
| `domain/agent_pipeline_snapshot.py` | Source for Agent Operations. |
| `domain/orchestration_run_snapshot.py` | Source for Evidence/Mission Control. |
| `domain/execution_library_snapshot.py` | Source for Mission Control/Execution. |
| `domain/notes_memory_snapshot.py` | Source for Memory Workspace. |

---

## 4. Files That Must Be Modified

| File | What to change |
|------|----------------|
| `ui/shell/application_shell.py` | Insert `GlobalContextBar`; replace static palette with `OSPalette`; bind new keybindings. |
| `ui/components/sidebar.py` | Group items into sections; support collapsible groups; reorder. |
| `ui/design_system/command.py` | Split/refactor into `OSPalette` with sections and provider registry. |
| `ui/shell/state_applier.py` | Apply state to context bar, new views, updated inspectors. |
| `ui/shell/view_manager.py` | Register `brain`, `evidence`, `operations`, `graph_workspace`, `insights`; set `command_center` default; order `VIEW_IDS`. |
| `ui/app.py` | Make `command_center` the unconditional default view. |
| `ui/controller.py` | Add `publish_context_*`, `publish_memory_*`, `publish_goal_*`, `publish_agent_*`, `publish_world_*`, `publish_evidence_*`, `publish_operation_*`, `publish_graph_*`, `publish_insights_*`. |
| `core/events/topics.py` | Add all missing UI topics. |
| `core/app_state.py` | Add `global_context`, `evidence_state`, `operations_state`, `insights_state` (or composite reducers). |
| `core/state/inspector_state.py` | Add navigation map entries for new inspector kinds. |
| `ui/views/goal_view.py` | Add goal tree, task detail, success criteria, inspector hooks. |
| `ui/views/agents_view.py` | Add run timelines, pipeline stage visualization, inspector hooks. |
| `ui/views/memory_view.py` | Add search, detail pane, injection indicator, inspector hooks. |
| `ui/views/world_explorer_view.py` | Add graph canvas, node filters, inspector docking. |
| `ui/views/relationship_view.py` | Expose reusable graph renderer for full graph workspace. |
| `ui/views/chat/chat_view.py` | Switch fully to `InspectorHost`/`InspectorDock`; remove local `ExecutionInspector` direct use if redundant. |
| `ui/components/inspector/execution_inspector.py` | Update import paths after relocating tab modules. |
| `ui/components/keyboard_shortcuts_overlay.py` | Update shortcut help for new nav/palette commands. |
| `orchestration/verification/truth_boundary.py` | Ensure truth validation results are available in `OrchestrationRunSnapshot` for Evidence workspace. |

---

## 5. Duplicate Implementations That Should Be Removed

| Duplicate | Resolution |
|-----------|------------|
| `ui/views/home_view.py` vs `ui/views/command_center_view.py` | `HomeView` is largely superseded by `CommandCenterView`. **Keep `CommandCenterView`**, remove `home` from default nav, and redirect `home` → `command_center`. Port any unique `HomeView` widgets (quick actions, activity feed) into `CommandCenterView`. |
| `ui/views/chat/inspector/*_tab.py` vs `ui/components/inspector/*.py` | The `chat/inspector` tab modules are **already imported by `ExecutionInspector`**. They are not dead code, but their path is misleading. **Relocate** `ui/views/chat/inspector/*.py` to `ui/components/inspector/tabs/` (or similar) and update `ExecutionInspector` imports. Do not delete them. |
| `ui/views/chat_view.py` top-level facade | It is a backward-compatible re-export of `ui.views.chat.chat_view.ChatView`. Safe to keep, but can be removed once all imports use `ui.views.chat.chat_view` directly. |
| `placeholder.py` (main) | Already deleted in HEAD. For insights, create a specific `insights_view.py` instead of reintroducing a generic placeholder. |
| `ui/components/chat_history_panel.py` vs `ui/views/chat/chat_history_panel.py` | The roadmap incorrectly listed `ui/views/chat/chat_history_panel.py`; **only `ui/components/chat_history_panel.py` exists** and should be reused. |

---

## 6. Updated Implementation Roadmap — Evolution Plan

### Dependency graph

```text
PR-UI-E00 Consolidation & Relocation
  └── PR-UI-E01 Universal Inspector Extension
        └── PR-UI-E02 Global Context Bar
              └── PR-UI-E03 OS Palette
                    └── PR-UI-E04 Navigation Shell
                          ├── PR-UI-E05 Memory Workspace
                          ├── PR-UI-E06 Brain Inspector
                          ├── PR-UI-E08 World Model Explorer
                          ├── PR-UI-E09 Agent Operations Center
                          └── PR-UI-E13 Insights Placeholder
PR-UI-E06 ──> PR-UI-E07 Goal Workspace
PR-UI-E08 ──> PR-UI-E12 Relationship Graph Workspace
PR-UI-E09 ──> PR-UI-E10 Evidence Workspace
PR-UI-E10 ──> PR-UI-E11 Mission Control Operations
```

### Migration order

| Phase | PR | Depends on | Parallelizable |
|-------|----|------------|----------------|
| 1 | PR-UI-E00 Consolidation & Relocation | — | No |
| 2 | PR-UI-E01 Universal Inspector Extension | E00 | No |
| 3 | PR-UI-E02 Global Context Bar | E01 | No |
| 4 | PR-UI-E03 OS Palette | E02 | No |
| 5 | PR-UI-E04 Navigation Shell | E03 | No |
| 6 | PR-UI-E05 Memory Workspace | E01, E04 | Yes with E06/E08/E09 |
| 6 | PR-UI-E06 Brain Inspector | E01, E04 | Yes with E05/E08/E09 |
| 6 | PR-UI-E08 World Model Explorer | E01, E04 | Yes with E05/E06/E09 |
| 6 | PR-UI-E09 Agent Operations Center | E01, E04 | Yes with E05/E06/E08 |
| 6 | PR-UI-E13 Insights Placeholder | E04 | Yes |
| 7 | PR-UI-E07 Goal Workspace | E06 | Yes with E10 |
| 7 | PR-UI-E10 Evidence Workspace | E09 | Yes with E07 |
| 7 | PR-UI-E11 Mission Control Operations | E10 | No |
| 7 | PR-UI-E12 Relationship Graph Workspace | E08 | No |

---

### PR Breakdown

#### PR-UI-E00 — Consolidation & Relocation

- **Purpose**: Remove dashboard duplication, clean up inspector module locations, and make `command_center` the unconditional default.
- **Files**:
  - Modify:
    - `ui/views/home_view.py` (add redirect or merge remaining widgets)
    - `ui/views/command_center_view.py` (absorb any unique home widgets)
    - `ui/shell/view_manager.py` (remove `home` registry or redirect to `command_center`)
    - `ui/components/sidebar.py` (remove `home` entry or move to bottom/archive group)
    - `ui/shell/application_shell.py` (remove `home` from palette; ensure default is `command_center`)
    - `ui/shell/state_applier.py` (remove `_home_view` apply)
    - `ui/app.py` (make `command_center` unconditional default)
    - `ui/components/inspector/execution_inspector.py` (update tab import paths after move)
  - Move (do not delete):
    - `ui/views/chat/inspector/inspector_artifacts_tab.py` → `ui/components/inspector/tabs/inspector_artifacts_tab.py`
    - `ui/views/chat/inspector/inspector_metrics_tab.py` → `ui/components/inspector/tabs/inspector_metrics_tab.py`
    - `ui/views/chat/inspector/inspector_provider_tab.py` → `ui/components/inspector/tabs/inspector_provider_tab.py`
    - `ui/views/chat/inspector/inspector_trace_tab.py` → `ui/components/inspector/tabs/inspector_trace_tab.py`
  - Delete:
    - `ui/views/chat/inspector/` directory (after move)
    - `ui/views/chat_view.py` facade (optional; safe to keep for compatibility)
- **Acceptance**: `home` redirects to `command_center`; no import errors; inspector tabs still render in `ExecutionInspector`.
- **Risk**: Medium (path renames). **Size**: Medium.

---

#### PR-UI-E01 — Universal Inspector Extension

- **Purpose**: Add new inspector kinds and make `InspectorHost` the single rail for every workspace.
- **Files**:
  - Modify:
    - `ui/components/inspector/inspector_host.py` (add breadcrumb, navigate button, default widget handling)
    - `ui/components/inspector/base_inspector.py` (stabilize contract)
    - `core/state/inspector_state.py` (extend kind-to-view map)
    - `core/events/topics.py` (add `UI_INSPECT_*` for new kinds)
    - `ui/controller.py` (publish inspect intents for new kinds)
    - `ui/shell/state_applier.py` (route inspector selection to all views with `InspectorDock`)
    - `ui/views/chat/chat_view.py` (switch fully to `InspectorHost`/`InspectorDock`)
  - New:
    - `ui/components/inspector/goal_inspector.py`
    - `ui/components/inspector/task_inspector.py`
    - `ui/components/inspector/memory_inspector.py`
    - `ui/components/inspector/agent_inspector.py`
    - `ui/components/inspector/note_inspector.py`
    - `ui/components/inspector/world_node_inspector.py`
    - `ui/components/inspector/execution_event_inspector.py`
    - `tests/ui/components/test_inspector_host.py`
- **Acceptance**: every `InspectableRef` kind renders an inspector; double-click navigates to owning workspace.
- **Risk**: Medium. **Size**: Large.

---

#### PR-UI-E02 — Global Context Bar

- **Purpose**: Move chat-local context into a shell-wide bar visible in every workspace.
- **Files**:
  - Modify:
    - `ui/shell/application_shell.py` (insert `GlobalContextBar` below `TopBar`)
    - `core/app_state.py` (add `global_context` reducer or reuse `chat_context_sources`/`chat_token_estimate`/`selected_entity_*`)
    - `core/state/chat_state.py` (promote context fields to global)
    - `core/events/topics.py` (add `UI_CONTEXT_*`)
    - `ui/shell/state_applier.py` (update context bar each refresh)
    - `ui/controller.py` (publish context select intents)
    - `ui/design_system/theme_v2.py` (context bar tokens)
  - New:
    - `ui/components/global_context_bar.py`
    - `core/state/global_context_state.py` (optional)
    - `tests/ui/components/test_global_context_bar.py`
- **Acceptance**: context bar shows active goal, selected entity, injected memories, model/provider, token budget across all views.
- **Risk**: Medium. **Size**: Medium.

---

#### PR-UI-E03 — OS Palette

- **Purpose**: Refactor `CommandPalette` into an extensible, context-aware OS kernel surface.
- **Files**:
  - Modify:
    - `ui/design_system/command.py` (refactor `CommandPalette` to `OSPalette` with sections)
    - `ui/shell/application_shell.py` (replace static `_show_command_palette` with provider-driven palette)
    - `ui/controller.py` (add palette provider registration helpers)
    - `core/events/topics.py` (add `UI_PALETTE_ACTION`, `PALETTE_PROVIDER_REGISTER`)
  - New:
    - `ui/design_system/palette_provider.py`
    - `tests/ui/test_os_palette.py`
- **Acceptance**: `Ctrl+K` opens palette with static + dynamic sections; new providers can register commands.
- **Risk**: Medium. **Size**: Large.

---

#### PR-UI-E04 — Navigation Shell

- **Purpose**: Regroup the sidebar into collapsible sections and finalize default routing.
- **Files**:
  - Modify:
    - `ui/components/sidebar.py` (group nav, section headers)
    - `ui/shell/view_manager.py` (`VIEW_IDS` ordering, remove `home`)
    - `ui/shell/application_shell.py` (adjust layout if needed)
    - `ui/components/keyboard_shortcuts_overlay.py` (update shortcut help)
    - `docs/architecture/ACC_UI_REFURBISHMENT.md` (nav design update)
  - New:
    - `ui/components/nav_group.py` (optional)
- **Acceptance**: sidebar grouped into Ops/Monitor/Library/Settings; `command_center` is default.
- **Risk**: Low. **Size**: Medium.

---

#### PR-UI-E05 — Memory Workspace

- **Purpose**: Evolve `MemoryView` into a full workspace with search, detail, injection indicator, and inspector.
- **Files**:
  - Modify:
    - `ui/views/memory_view.py` (add search, detail, injection badge, inspector hooks)
    - `ui/shell/view_manager.py` (ensure `memory` workspace registration)
    - `ui/shell/state_applier.py` (apply memory state)
    - `ui/components/sidebar.py` (place memory in correct group)
    - `ui/controller.py` (publish `UI_MEMORY_*` intents)
    - `core/events/topics.py` (add `UI_MEMORY_*`)
  - New:
    - `ui/components/memory/memory_card.py`
    - `ui/components/memory/memory_detail.py`
    - `core/state/memory_state.py` (optional)
    - `tests/ui/views/test_memory_workspace_view.py`
- **Acceptance**: memory workspace shows catalog, search, detail; injection indicator matches context bar.
- **Risk**: Low-Medium. **Size**: Medium.

---

#### PR-UI-E06 — Brain Inspector

- **Purpose**: New `BrainView` workspace exposing `BrainStateSnapshot` (kernel, goals, observations, actions, plan).
- **Files**:
  - Modify:
    - `ui/shell/view_manager.py` (register `brain`)
    - `ui/shell/state_applier.py` (apply `brain_state`)
    - `ui/components/sidebar.py` (add `brain` entry)
    - `ui/controller.py` (publish brain inspect/select)
    - `core/events/topics.py` (add `UI_BRAIN_*` or reuse `UI_INSPECT_*`)
  - New:
    - `ui/views/brain_view.py`
    - `ui/components/brain/goal_card.py`
    - `ui/components/brain/observation_card.py`
    - `ui/components/brain/action_card.py`
    - `ui/components/brain/plan_card.py`
    - `tests/ui/views/test_brain_view.py`
- **Acceptance**: brain workspace shows kernel, active goal, observations, runtime actions, current plan.
- **Risk**: Medium. **Size**: Medium.

---

#### PR-UI-E07 — Goal Workspace

- **Purpose**: Evolve `GoalView` into a full goal operations center with tree, task detail, success criteria, inspector.
- **Files**:
  - Modify:
    - `ui/views/goal_view.py` (or rename to `goal_workspace_view.py`)
    - `ui/shell/state_applier.py` (apply goal/brain state)
    - `ui/shell/view_manager.py` (update `goals` factory)
    - `ui/controller.py` (publish `UI_GOAL_*`)
    - `core/events/topics.py` (add `UI_GOAL_*`)
    - `domain/brain_state_snapshot.py` (ensure plan/task fields)
  - New:
    - `ui/components/goal/goal_tree.py`
    - `ui/components/goal/task_row.py`
    - `ui/components/goal/success_criteria_card.py`
    - `ui/components/goal/goal_detail.py`
    - `tests/ui/views/test_goal_workspace_view.py`
- **Acceptance**: goal workspace shows goal tree, tasks, success criteria; inspector shows selected goal/task.
- **Risk**: Medium. **Size**: Large.

---

#### PR-UI-E08 — World Model Explorer

- **Purpose**: Enhance `WorldExplorerView` with graph canvas, filters, and inspector docking.
- **Files**:
  - Modify:
    - `ui/views/world_explorer_view.py` (add graph, filters, inspector)
    - `ui/views/relationship_view.py` (expose reusable graph renderer)
    - `ui/components/graph_canvas.py` (generalize or create `WorldGraphCanvas`)
    - `ui/shell/state_applier.py` (apply world model state)
    - `ui/controller.py` (publish `UI_WORLD_*`)
    - `core/events/topics.py` (add `UI_WORLD_*`)
    - `core/state/world_model_state.py` (add selected node, layout)
  - New:
    - `ui/components/world_model/node_filters.py`
    - `ui/components/world_model/world_graph_canvas.py` (optional)
    - `tests/ui/views/test_world_explorer_view.py`
- **Acceptance**: world explorer shows list, filters, graph; node selection updates inspector/relationships.
- **Risk**: Medium-High. **Size**: Large.

---

#### PR-UI-E09 — Agent Operations Center

- **Purpose**: Evolve `AgentsView` into a mission-control roster with run timelines, pipeline stage, and inspector.
- **Files**:
  - Modify:
    - `ui/views/agents_view.py` (or rename)
    - `ui/shell/state_applier.py` (apply agent pipeline)
    - `ui/shell/view_manager.py` (update `agents` factory)
    - `ui/controller.py` (publish `UI_AGENT_*`)
    - `core/events/topics.py` (add `UI_AGENT_*`)
  - New:
    - `ui/components/agent/agent_card.py`
    - `ui/components/agent/run_timeline.py`
    - `ui/components/agent/pipeline_stage.py`
    - `tests/ui/views/test_agent_operations_view.py`
- **Acceptance**: agent ops shows active runs, pipeline stage, planned tools; inspector shows selected run.
- **Risk**: Medium. **Size**: Large.

---

#### PR-UI-E10 — Evidence Workspace

- **Purpose**: New `EvidenceView` for claims, truth validation, execution facts, and receipts.
- **Files**:
  - Modify:
    - `ui/shell/view_manager.py` (register `evidence`)
    - `ui/shell/state_applier.py` (apply evidence state)
    - `ui/components/sidebar.py` (add `evidence` entry)
    - `ui/controller.py` (publish `UI_EVIDENCE_*`)
    - `core/events/topics.py` (add `UI_EVIDENCE_*`)
    - `core/app_state.py` (add `evidence_state` reducer or reuse `orchestration_run`/`execution_library`)
    - `orchestration/verification/truth_boundary.py` (ensure snapshotable truth results)
  - New:
    - `ui/views/evidence_view.py`
    - `ui/components/evidence/claim_card.py`
    - `ui/components/evidence/truth_badge.py`
    - `ui/components/evidence/receipt_chain.py`
    - `tests/ui/views/test_evidence_view.py`
- **Acceptance**: evidence list shows claims with truth status; selecting shows facts, receipt, trace.
- **Risk**: Medium. **Size**: Large.

---

#### PR-UI-E11 — Mission Control Operations

- **Purpose**: New `OperationsView` showing the live pipeline and timeline scrubber.
- **Files**:
  - Modify:
    - `ui/shell/view_manager.py` (register `operations`)
    - `ui/shell/state_applier.py` (apply operations state)
    - `ui/components/sidebar.py` (add `operations` entry)
    - `ui/controller.py` (publish `UI_OPERATION_*`)
    - `core/events/topics.py` (add `UI_OPERATION_*`)
    - `core/app_state.py` (add `operations_state` reducer or reuse `operation_library_index`/`operation_journal`)
    - `ui/components/docks/execution_timeline_dock.py` (reuse)
  - New:
    - `ui/views/operations_view.py`
    - `ui/components/operations/pipeline_stage.py`
    - `ui/components/operations/operation_card.py`
    - `tests/ui/views/test_operations_view.py`
- **Acceptance**: operations view shows pipeline stages and timeline; scrubber updates inspector.
- **Risk**: Medium-High. **Size**: Large.

---

#### PR-UI-E12 — Relationship Graph Workspace

- **Purpose**: New `GraphWorkspaceView` reusing `graph_canvas.py` and `relationship_view.py`.
- **Files**:
  - Modify:
    - `ui/shell/view_manager.py` (register `graph_workspace`)
    - `ui/shell/state_applier.py` (apply full graph state)
    - `ui/components/sidebar.py` (add `graph_workspace` entry)
    - `ui/controller.py` (publish `UI_GRAPH_*`)
    - `core/events/topics.py` (add `UI_GRAPH_*`)
    - `ui/components/graph_canvas.py` (add world-model renderer adapter)
    - `ui/views/relationship_view.py` (expose reusable renderer)
  - New:
    - `ui/views/graph_workspace_view.py`
    - `ui/components/world_model/graph_renderer.py`
    - `tests/ui/views/test_graph_workspace_view.py`
- **Acceptance**: full graph renders all nodes/edges; filters/search work; double-click navigates.
- **Risk**: High. **Size**: Large.

---

#### PR-UI-E13 — Insights Placeholder

- **Purpose**: Reserve `insights` workspace for Phase 10+ with a stub view, sidebar entry, topics, and state file.
- **Files**:
  - Modify:
    - `ui/shell/view_manager.py` (register `insights`)
    - `ui/components/sidebar.py` (add `insights` entry)
    - `core/events/topics.py` (add `UI_INSIGHTS_*`)
    - `core/app_state.py` (add `insights_state` reducer)
  - New:
    - `ui/views/insights_view.py`
    - `core/state/insights_state.py`
    - `tests/ui/views/test_insights_view.py`
- **Acceptance**: `insights` view registered, reachable from sidebar, shows Phase 10 placeholder.
- **Risk**: Low. **Size**: Small.

---

### Hot spots for evolution

- `core/app_state.py` and `ui/shell/state_applier.py` are touched by nearly every PR; keep additions isolated to new reducer functions and `apply_state` branches.
- `ui/shell/application_shell.py` is edited by E00–E04; sequence matters.
- `graph_canvas.py` is workflow-oriented; world-model graph should be implemented via an adapter or separate `WorldGraphCanvas` to avoid breaking workflow graph.
- `ui/views/chat/inspector/*` tab modules are **not dead code**; they feed `ExecutionInspector`. Relocate them instead of deleting.

---

### Verification

After each evolution PR:

```bash
python3 -m pytest -m "not slow"
python3 -m ruff check ai_command_center
python3 scripts/verify_ui_constitution.py
python3 scripts/verify_constitution.py
```

For palette/inspector PRs, also run:

```bash
python3 -m pytest tests/ui/
```

---

## Summary

The Phase B UI work should not be a rewrite. `origin/main` already provides the inspector framework, command palette, top bar, sidebar, chat, world/relationship explorers, and execution views. The `phase-11a-command-center` branch already adds Command Center, Top Bar live wiring, Goal/Agent/Approval views, and consolidated snapshots.

The evolution plan above is a **gap-filling, extension-first** sequence that:

1. Consolidates and relocates misleading paths.
2. Extends the universal inspector.
3. Adds the Global Context Bar and OS Palette.
4. Reorganizes navigation.
5. Hardens each Workspace OS view incrementally (Memory, Brain, Goal, Agent, World, Evidence, Operations, Graph, Insights).

This reduces risk, reuses the existing UI Constitution and `StateApplierMixin` patterns, and avoids duplicate implementation.
