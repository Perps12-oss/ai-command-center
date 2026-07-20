# Phase B UI Implementation Roadmap — Evolution Plan (Canon-corrected)

- **Baseline:** `origin/main` @ `e128a72` (sole source of truth for what exists)
- **Canon artifact:** `docs/audits/REPOSITORY_TRUTH_CANON.md` (`cursor/repository-truth-canon-2c79` @ `764796a`)
- **Superseded audit:** `REPOSITORY_TRUTH_AUDIT.md` on `phase-11a-command-center` @ `8ba0522` is non-canonical
- **Superseded branch:** `phase-11a-command-center` is stale; close PR #75
- **Branch rule:** All Phase B PRs branch from `origin/main`

This is the canon-corrected evolution roadmap for Phase B. It replaces any prior Phase B plan that used `phase-11a-command-center` as its baseline.

---

## 1. Canonical inventory on `origin/main`

### Workspace shells and panel packages

| Workspace | Shell | Panel package | Introduced |
|-----------|-------|---------------|------------|
| **Command Center** | `ai_command_center/ui/views/command_center_view.py` | — | `423006a` (#76) |
| **Goal Dashboard** | `ai_command_center/ui/views/goal_view.py` | `ai_command_center/ui/views/goal_dashboard/` (7 files) | shell `423006a` (#76), package `811e847` (#79) |
| **Agent Monitor** | `ai_command_center/ui/views/agents_view.py` | `ai_command_center/ui/views/agent_monitor/` (6 files) | `5ae710d` (#77) |
| **Execution Center** | `ai_command_center/ui/views/executions_view.py` | `ai_command_center/ui/views/execution_center/` (6 files) | `423006a` (#76) |
| **World Model** | `ai_command_center/ui/views/world_explorer_view.py` | `ai_command_center/ui/views/world_model/` (5 files) | `423006a` (#76) |
| **Approval Center** | `ai_command_center/ui/views/approvals_view.py` | — | `423006a` (#76) |

### Shared graph / timeline primitives

| Primitive | Path | Role |
|-----------|------|------|
| `BaseGraphCanvas` | `ai_command_center/ui/components/graph/base_graph_canvas.py` | Shared graph engine (#78) |
| `GraphCanvas` | `ai_command_center/ui/components/graph_canvas.py` | Workflow adapter that subclasses `BaseGraphCanvas` |
| `GraphNodeVisual` / `GraphEdgeVisual` / `circular_layout` | `ai_command_center/ui/components/graph/` | Graph visuals and layouts |
| `TimelineRenderer` | `ai_command_center/ui/components/timeline_renderer.py` | Timeline primitive |
| `ExecutionTimelineDock` | `ai_command_center/ui/components/docks/execution_timeline_dock.py` | Hosts `TimelineRenderer` |

### Foundation already on `origin/main`

- `InspectorHost`, `BaseInspector`, typed inspectors (`message`, `artifact`, `provider`, `decision`, `execution`, `payload`, `workflow_node`), `InspectorDock`
- `CommandPalette`, `TopBar`, `Sidebar`, `ViewManager`
- `UIController` / `WorkspaceOsUIController`, `state_applier`, `app_state`, `topics.py`
- `ui/views/surface_state.py` (Article 18 empty/loading/error surfaces)

### Existence matrix

| Path | `origin/main` | `origin/phase-11a-command-center` |
|------|:-------------:|:---------------------------------:|
| `ui/views/goal_dashboard/` | ✅ | ❌ |
| `ui/views/agent_monitor/` | ✅ | ❌ |
| `ui/views/execution_center/` | ✅ | ❌ |
| `ui/components/graph/base_graph_canvas.py` | ✅ | ❌ |
| `ui/views/world_model/selection_inspector_panel.py` | ✅ | ❌ |
| `ui/views/world_model/knowledge_graph_panel.py` | ✅ | ❌ |
| `ui/components/timeline_renderer.py` | ✅ | ✅ |
| `ui/views/command_center_view.py` | ✅ | ✅ |
| `ui/views/goal_view.py` | ✅ | ✅ |
| `ui/views/agents_view.py` | ✅ | ✅ |
| `ui/views/approvals_view.py` | ✅ | ✅ |

---

## 2. Composition model (do not flatten)

```text
GoalView        ──imports──► ui/views/goal_dashboard/*
AgentsView      ──imports──► ui/views/agent_monitor/*
ExecutionsView  ──imports──► ui/views/execution_center/*
WorldExplorerView ──imports──► ui/views/world_model/*
                                  ├── KnowledgeGraphPanel → BaseGraphCanvas
                                  └── SelectionInspectorPanel
GraphCanvas (workflow) ──subclasses──► BaseGraphCanvas
```

The shell files (`*_view.py`) are **orchestrators** that compose packages of panels. Auditing only for `*_view.py` filenames and ignoring the packages produces false “concept only” results. Phase B must evolve the packages, not replace them.

---

## 3. Mandatory reuse rules (binding)

1. **Graph primitive:** `BaseGraphCanvas` is the shared graph engine. Adapters and subclasses are OK; a second engine (e.g. `WorldGraphCanvas`) is not.
2. **Timeline primitive:** `TimelineRenderer` + `ExecutionTimelineDock` are the shared timeline engine. No parallel `run_timeline` engine.
3. **Inspector primitive:** Extend `InspectorHost` / `InspectorDock`. Reconcile `SelectionInspectorPanel` by composition into the inspector rail, not by creating a third inspector OS.
4. **Evolve, do not rewrite:** `GoalView`, `AgentsView`, `ExecutionsView`, and `WorldExplorerView` already compose their panel packages. Phase B adds global OS integration, inspector wiring, topics, and cross-panel selection — it does not rewrite the shells or panels from scratch.
5. **AppState policy:** Each PR must state whether it is composition-only (reuses existing snapshots) or requires an AppState amendment before coding begins.
6. **Branch from `main`:** Phase B PRs branch from `origin/main`. `phase-11a-command-center` and PR #75 are not sources of truth.

---

## 4. Remaining Phase B gaps (evolution)

| # | Gap | Why it remains |
|---|-----|----------------|
| 1 | **Global Context Bar** | No shell-wide context widget below `TopBar`. |
| 2 | **OS Palette provider system** | `CommandPalette` is static; no provider registry, context sections, or dynamic scoping. |
| 3 | **Navigation Shell grouping** | `Sidebar` is a flat list; needs collapsible groups (Ops / Monitor / Library / Settings). |
| 4 | **Memory Workspace hardening** | `MemoryView` is a simple list; missing search, detail pane, injection indicator, inspector. |
| 5 | **Brain Inspector workspace** | No dedicated `BrainView` for kernel state, goals, observations, actions, plan. |
| 6 | **Goal Workspace hardening** | `GoalView` + `goal_dashboard` package exist; missing inspector wiring, `UI_GOAL_*` topics, cross-panel selection, success-criteria/task detail integration. |
| 7 | **Agent Operations Center hardening** | `AgentsView` + `agent_monitor` package exist; missing inspector wiring, `UI_AGENT_*` topics, cross-panel selection, run timeline scrubber. |
| 8 | **Execution Center hardening** | `ExecutionsView` + `execution_center` package exist; missing inspector wiring, `UI_EXECUTION_*` topics, mission-control layout. |
| 9 | **World Model Explorer hardening** | `WorldExplorerView` + `world_model` package exist; missing inspector docking (`SelectionInspectorPanel` → `InspectorHost`), palette commands, `UI_WORLD_*` topics. |
| 10 | **Evidence Workspace** | No `EvidenceView`; can reuse `execution_center.ReceiptViewerPanel` and `TruthValidationPanel` plus a claim list. |
| 11 | **Mission Control Operations** | No `OperationsView` for live `Planner → Router → Executor → Verifier → Receipt` pipeline with `ExecutionTimelineDock`. |
| 12 | **Relationship Graph Workspace** | No full-graph workspace; build a new shell that reuses `KnowledgeGraphPanel` and `SelectionInspectorPanel` on `BaseGraphCanvas`. |
| 13 | **Insights Placeholder** | No `insights` view, state, or sidebar entry. |
| 14 | **Extended inspector kinds** | `InspectorHost` only registers `message`, `artifact`, `provider`, `decision`. Missing `goal`, `task`, `memory`, `agent`, `note`, `world_node`, `execution_event`. |
| 15 | **UI-level EventBus topics** | Missing `UI_CONTEXT_*`, `UI_MEMORY_*`, `UI_GOAL_*`, `UI_AGENT_*`, `UI_EXECUTION_*`, `UI_WORLD_*`, `UI_EVIDENCE_*`, `UI_OPERATION_*`, `UI_GRAPH_*`, `UI_INSIGHTS_*`. |
| 16 | **Composite state projections** | No `global_context`, `evidence_state`, `operations_state`, `graph_state`, or `insights_state` projections. |

---

## 5. Reuse, modify, and retire

### Reuse/extend (do not rewrite)

| Asset | How to reuse |
|-------|--------------|
| `BaseGraphCanvas` | All graph surfaces must project through it. `KnowledgeGraphPanel` already uses it; `GraphCanvas` subclasses it. |
| `TimelineRenderer` / `ExecutionTimelineDock` | Use for agent run timelines, execution timeline, and mission control scrubber. |
| `InspectorHost` / `InspectorDock` | Add new kind registrations; host `SelectionInspectorPanel` content by composition. |
| `goal_dashboard/*` panels | Extend for task detail, success criteria, inspector selection. |
| `agent_monitor/*` panels | Extend for per-agent inspector, run timeline scrubber, pipeline stage drill-down. |
| `execution_center/*` panels | Reuse for execution list/detail/timeline/receipt/truth in both `ExecutionsView` and `EvidenceView`. |
| `world_model/*` panels | Reuse `KnowledgeGraphPanel` and `SelectionInspectorPanel` for full graph workspace. |
| `CommandCenterView` | Absorb any remaining `HomeView` widgets; keep as default. |
| `TopBar` / `Sidebar` / `ViewManager` / `state_applier` / `controller` / `app_state` / `topics` | Add wiring for new OS features and views. |

### Modify

| File | What to change |
|------|----------------|
| `ui/shell/application_shell.py` | Insert `GlobalContextBar`; replace static palette with provider-driven `OSPalette`; bind new keybindings. |
| `ui/components/sidebar.py` | Group `NAV_ITEMS` into collapsible sections; remove/archive `home`. |
| `ui/shell/view_manager.py` | Register `brain`, `evidence`, `operations`, `graph_workspace`, `insights`; ensure `command_center` default; order `VIEW_IDS`. |
| `ui/app.py` | Make `command_center` unconditional default if not already. |
| `ui/shell/state_applier.py` | Apply state to context bar, new views, inspector docking, existing workspace shells. |
| `ui/controller.py` | Add intent publishers for `UI_CONTEXT_*`, `UI_MEMORY_*`, `UI_GOAL_*`, `UI_AGENT_*`, `UI_EXECUTION_*`, `UI_WORLD_*`, `UI_EVIDENCE_*`, `UI_OPERATION_*`, `UI_GRAPH_*`, `UI_INSIGHTS_*`. |
| `core/events/topics.py` | Append new UI topics. |
| `core/app_state.py` | Add `global_context`, `evidence_state`, `operations_state`, `graph_state`, `insights_state` reducers or compose from existing snapshots. |
| `ui/design_system/command.py` | Refactor `CommandPalette` into `OSPalette` with sections and provider registry. |
| `ui/views/memory_view.py` | Add search, detail pane, injection indicator, inspector hooks. |
| `ui/views/goal_view.py` | Add inspector wiring, `UI_GOAL_*` topic callbacks, cross-panel selection, success-criteria/task detail. |
| `ui/views/agents_view.py` | Add inspector wiring, `UI_AGENT_*` topic callbacks, per-agent selection, run timeline scrubber. |
| `ui/views/executions_view.py` | Add inspector wiring, `UI_EXECUTION_*` topic callbacks, mission-control layout polish. |
| `ui/views/world_explorer_view.py` | Add `InspectorDock` integration, route `SelectionInspectorPanel` into `InspectorHost`, palette commands. |
| `ui/components/inspector/inspector_host.py` | Register new inspector kinds; support `SelectionInspectorPanel` content. |
| `core/state/inspector_state.py` | Extend kind-to-view navigation map. |
| `domain/inspectable.py` | Add factory helpers for new kinds. |

### Retire / avoid

| Item | Resolution |
|------|------------|
| `phase-11a-command-center` / PR #75 | Close; do not use as baseline. |
| `REPOSITORY_TRUTH_AUDIT.md` @ `8ba0522` | Non-canonical; use `docs/audits/REPOSITORY_TRUTH_CANON.md` instead. |
| `ui/views/home_view.py` | `HomeView` is superseded by `CommandCenterView`. Remove from default navigation; redirect `home` → `command_center`; port any unique widgets. |
| `ui/views/chat/inspector/*_tab.py` | These tab modules are imported by `ExecutionInspector`. If still under `chat/inspector`, relocate to `ui/components/inspector/tabs/` and update imports. |
| `WorldGraphCanvas` engine | Do not create. Build adapters over `BaseGraphCanvas` instead. |
| Parallel `run_timeline` engine | Do not create. Use `TimelineRenderer` + `ExecutionTimelineDock`. |

---

## 6. Updated PR breakdown

### Dependency graph

```text
PR-UI-E00 Canon Alignment & Consolidation
  └── PR-UI-E01 Universal Inspector Extension
        └── PR-UI-E02 Global Context Bar
              └── PR-UI-E03 OS Palette
                    └── PR-UI-E04 Navigation Shell
                          ├── PR-UI-E05 Memory Workspace Hardening
                          ├── PR-UI-E06 Brain Inspector
                          ├── PR-UI-E08 World Model Explorer Hardening
                          ├── PR-UI-E09 Agent Operations Center Hardening
                          └── PR-UI-E13 Insights Placeholder
PR-UI-E06 ──> PR-UI-E07 Goal Workspace Hardening
PR-UI-E08 ──> PR-UI-E12 Relationship Graph Workspace
PR-UI-E09 ──> PR-UI-E10 Evidence Workspace
PR-UI-E10 ──> PR-UI-E11 Mission Control Operations
```

### Migration order

| Phase | PR | Depends on | Parallelizable |
|-------|----|------------|----------------|
| 1 | PR-UI-E00 Canon Alignment & Consolidation | — | No |
| 2 | PR-UI-E01 Universal Inspector Extension | E00 | No |
| 3 | PR-UI-E02 Global Context Bar | E01 | No |
| 4 | PR-UI-E03 OS Palette | E02 | No |
| 5 | PR-UI-E04 Navigation Shell | E03 | No |
| 6 | PR-UI-E05 Memory Workspace Hardening | E01, E04 | Yes with E06/E08/E09 |
| 6 | PR-UI-E06 Brain Inspector | E01, E04 | Yes with E05/E08/E09 |
| 6 | PR-UI-E08 World Model Explorer Hardening | E01, E04 | Yes with E05/E06/E09 |
| 6 | PR-UI-E09 Agent Operations Center Hardening | E01, E04 | Yes with E05/E06/E08 |
| 6 | PR-UI-E13 Insights Placeholder | E04 | Yes |
| 7 | PR-UI-E07 Goal Workspace Hardening | E06 | Yes with E10 |
| 7 | PR-UI-E10 Evidence Workspace | E09 | Yes with E07 |
| 7 | PR-UI-E11 Mission Control Operations | E10 | No |
| 7 | PR-UI-E12 Relationship Graph Workspace | E08 | No |

---

#### PR-UI-E00 — Canon Alignment & Consolidation

- **Purpose:** Baseline the repo on `origin/main`, close stale `phase-11a-command-center` assumptions, clean up any inspector tab path oddities, and make `command_center` the unconditional default.
- **Files:**
  - Modify:
    - `ui/app.py` (make `command_center` default)
    - `ui/views/home_view.py` (redirect/merge remaining widgets)
    - `ui/views/command_center_view.py` (absorb any unique home widgets)
    - `ui/shell/view_manager.py` (remove or redirect `home` registry; confirm `goals`, `agents`, `approvals`, `executions`, `world_explorer` are registered)
    - `ui/components/sidebar.py` (remove/archive `home` entry; add grouping placeholders)
    - `ui/shell/state_applier.py` (remove `_home_view` apply if present)
    - `ui/components/inspector/execution_inspector.py` (update tab import paths if still under `chat/inspector`)
  - Move (if still present):
    - `ui/views/chat/inspector/*_tab.py` → `ui/components/inspector/tabs/`
  - Delete:
    - `ui/views/chat/inspector/` directory (after move)
    - `ui/views/chat_view.py` facade (optional compatibility-only)
- **Acceptance:** `home` redirects to `command_center`; all existing workspace shells (`goals`, `agents`, `approvals`, `executions`, `world_explorer`) are reachable; no import errors.
- **Risk:** Medium. **Size:** Medium.

---

#### PR-UI-E01 — Universal Inspector Extension

- **Purpose:** Make every object inspectable from any workspace via `InspectorHost`/`InspectorDock`; reconcile `SelectionInspectorPanel` content by composition.
- **Files:**
  - Modify:
    - `ui/components/inspector/inspector_host.py` (add breadcrumb, navigate button, default widget, new kind registrations)
    - `ui/components/inspector/base_inspector.py` (stabilize contract)
    - `core/state/inspector_state.py` (extend kind-to-view map)
    - `core/events/topics.py` (add `UI_INSPECT_*` for new kinds)
    - `ui/controller.py` (publish inspect intents for new kinds)
    - `ui/shell/state_applier.py` (route inspector selection to all views with `InspectorDock`)
    - `ui/views/world_explorer_view.py` (route `SelectionInspectorPanel` content into `InspectorHost`)
    - `ui/views/chat/chat_view.py` (switch fully to `InspectorHost`/`InspectorDock` if not already)
  - New:
    - `ui/components/inspector/goal_inspector.py`
    - `ui/components/inspector/task_inspector.py`
    - `ui/components/inspector/memory_inspector.py`
    - `ui/components/inspector/agent_inspector.py`
    - `ui/components/inspector/note_inspector.py`
    - `ui/components/inspector/world_node_inspector.py`
    - `ui/components/inspector/execution_event_inspector.py`
    - `tests/ui/components/test_inspector_host.py`
    - `tests/ui/components/test_inspector_dock.py`
- **Acceptance:** every registered `InspectableRef` kind renders an inspector; `SelectionInspectorPanel` content is hosted in the inspector rail; double-click navigates to owning workspace.
- **Risk:** High. **Size:** Large.

---

#### PR-UI-E02 — Global Context Bar

- **Purpose:** Move chat-local context into a shell-wide bar visible in every workspace.
- **Files:**
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
- **Acceptance:** context bar shows active goal, selected entity, injected memories, model/provider, token budget across all views.
- **Risk:** Medium. **Size:** Medium.

---

#### PR-UI-E03 — OS Palette

- **Purpose:** Turn `CommandPalette` into an extensible, context-aware OS kernel surface.
- **Files:**
  - Modify:
    - `ui/design_system/command.py` (refactor `CommandPalette` to `OSPalette` with sections)
    - `ui/components/command_box.py` (palette trigger)
    - `ui/shell/application_shell.py` (replace static `_show_command_palette` with provider-driven palette)
    - `ui/controller.py` (add palette provider registration helpers)
    - `core/events/topics.py` (add `UI_PALETTE_ACTION`, `PALETTE_PROVIDER_REGISTER`)
  - New:
    - `ui/design_system/palette_provider.py`
    - `tests/ui/test_os_palette.py`
- **Acceptance:** `Ctrl+K` opens palette with static + dynamic sections; new providers can register commands.
- **Risk:** Medium. **Size:** Large.

---

#### PR-UI-E04 — Navigation Shell

- **Purpose:** Regroup the sidebar into collapsible sections and finalize default routing.
- **Files:**
  - Modify:
    - `ui/components/sidebar.py` (group nav, section headers)
    - `ui/shell/view_manager.py` (`VIEW_IDS` ordering, remove `home`)
    - `ui/shell/application_shell.py` (adjust layout if needed)
    - `ui/components/keyboard_shortcuts_overlay.py` (update shortcut help)
    - `docs/architecture/ACC_UI_REFURBISHMENT.md` (nav design update)
  - New:
    - `ui/components/nav_group.py` (optional)
- **Acceptance:** sidebar grouped as Ops / Monitor / Library / Settings; `command_center` is default; all `VIEW_IDS` still resolvable.
- **Risk:** Low. **Size:** Medium.

---

#### PR-UI-E05 — Memory Workspace Hardening

- **Purpose:** Evolve `MemoryView` into a full workspace with search, detail, injection indicator, and inspector.
- **Files:**
  - Modify:
    - `ui/views/memory_view.py` (add search, detail, injection badge, inspector hooks)
    - `ui/shell/view_manager.py` (ensure `memory` workspace registration)
    - `ui/shell/state_applier.py` (apply memory state)
    - `ui/components/sidebar.py` (place memory in Library group)
    - `ui/controller.py` (publish `UI_MEMORY_*` intents)
    - `core/events/topics.py` (add `UI_MEMORY_*`)
  - New:
    - `ui/components/memory/memory_card.py`
    - `ui/components/memory/memory_detail.py`
    - `core/state/memory_state.py` (optional)
    - `tests/ui/views/test_memory_workspace_view.py`
- **Acceptance:** memory workspace shows catalog, search, detail; injection indicator matches context bar.
- **Risk:** Low-Medium. **Size:** Medium.

---

#### PR-UI-E06 — Brain Inspector

- **Purpose:** New `BrainView` workspace exposing `BrainStateSnapshot` (kernel state, goals, observations, runtime actions, current plan).
- **Files:**
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
- **Acceptance:** brain workspace shows kernel, active goal, observations, runtime actions, current plan.
- **Risk:** Medium. **Size:** Medium.

---

#### PR-UI-E07 — Goal Workspace Hardening

- **Purpose:** Evolve the existing `GoalView` + `goal_dashboard` package into a fully integrated goal operations center. **Do not rewrite the package.**
- **Files:**
  - Modify:
    - `ui/views/goal_view.py` (add inspector hooks, `UI_GOAL_*` callbacks, cross-panel selection)
    - `ui/views/goal_dashboard/goal_detail_panel.py` (add success-criteria / task detail sections)
    - `ui/views/goal_dashboard/goal_list_panel.py` (emit select events)
    - `ui/shell/state_applier.py` (apply goal/brain state)
    - `ui/shell/view_manager.py` (update `goals` factory if needed)
    - `ui/controller.py` (publish `UI_GOAL_*`)
    - `core/events/topics.py` (add `UI_GOAL_*`)
    - `domain/brain_state_snapshot.py` (ensure plan/task fields are sufficient)
  - New:
    - `tests/ui/views/test_goal_workspace_view.py`
- **Acceptance:** goal workspace shows goal tree, task detail, success criteria; inspector shows selected goal/task; actions publish `UI_GOAL_*` events.
- **Risk:** Medium. **Size:** Medium-Large.

---

#### PR-UI-E08 — World Model Explorer Hardening

- **Purpose:** Evolve the existing `WorldExplorerView` + `world_model` package; integrate `SelectionInspectorPanel` content into `InspectorHost` and add `UI_WORLD_*` topics. **Use `BaseGraphCanvas` through `KnowledgeGraphPanel`; do not create a new graph engine.**
- **Files:**
  - Modify:
    - `ui/views/world_explorer_view.py` (add `InspectorDock`, palette commands, `UI_WORLD_*` callbacks)
    - `ui/views/world_model/selection_inspector_panel.py` (expose as inspector content, not a standalone OS)
    - `ui/shell/state_applier.py` (apply world model state)
    - `ui/controller.py` (publish `UI_WORLD_*`)
    - `core/events/topics.py` (add `UI_WORLD_*`)
    - `core/state/world_model_state.py` (add selected node, layout)
  - New:
    - `ui/components/world_model/node_filters.py` (if not present)
    - `tests/ui/views/test_world_explorer_view.py`
- **Acceptance:** world explorer shows list, filters, graph on `BaseGraphCanvas`; node selection updates inspector; no duplicate inspector surface.
- **Risk:** Medium. **Size:** Medium.

---

#### PR-UI-E09 — Agent Operations Center Hardening

- **Purpose:** Evolve the existing `AgentsView` + `agent_monitor` package; add inspector wiring, `UI_AGENT_*` topics, and run timeline scrubber.
- **Files:**
  - Modify:
    - `ui/views/agents_view.py` (add inspector hooks, `UI_AGENT_*` callbacks, cross-panel selection)
    - `ui/views/agent_monitor/active_agents_panel.py` (emit select events)
    - `ui/views/agent_monitor/agent_state_panel.py` (show per-agent detail)
    - `ui/views/agent_monitor/execution_history_panel.py` (integrate `ExecutionTimelineDock` / `TimelineRenderer`)
    - `ui/shell/state_applier.py` (apply agent pipeline)
    - `ui/shell/view_manager.py` (update `agents` factory if needed)
    - `ui/controller.py` (publish `UI_AGENT_*`)
    - `core/events/topics.py` (add `UI_AGENT_*`)
  - New:
    - `tests/ui/views/test_agent_operations_view.py`
- **Acceptance:** agent ops shows active runs, pipeline stage, planned tools; inspector shows selected run; timeline scrubber works; actions publish `UI_AGENT_*` events.
- **Risk:** Medium. **Size:** Medium-Large.

---

#### PR-UI-E10 — Evidence Workspace

- **Purpose:** New `EvidenceView` for claims, truth validation, execution facts, and receipts. Reuse `execution_center.ReceiptViewerPanel` and `TruthValidationPanel`.
- **Files:**
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
    - `ui/views/evidence/claim_list_panel.py` (optional package)
    - `tests/ui/views/test_evidence_view.py`
- **Acceptance:** evidence list shows claims with truth status; selecting a claim shows facts, receipt, trace; reuses existing truth/receipt panels.
- **Risk:** Medium. **Size:** Large.

---

#### PR-UI-E11 — Mission Control Operations View

- **Purpose:** New workspace showing the live `Planner → Router → Executor → Verifier → Receipt` pipeline with `ExecutionTimelineDock`.
- **Files:**
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
- **Acceptance:** operations view shows pipeline stages and timeline; scrubber updates inspector.
- **Risk:** Medium-High. **Size:** Large.

---

#### PR-UI-E12 — Relationship Graph Workspace

- **Purpose:** New full-graph workspace for the world model. **Reuses `KnowledgeGraphPanel` and `SelectionInspectorPanel` on `BaseGraphCanvas`; no new graph engine.**
- **Files:**
  - Modify:
    - `ui/shell/view_manager.py` (register `graph_workspace`)
    - `ui/shell/state_applier.py` (apply full graph state)
    - `ui/components/sidebar.py` (add `graph_workspace` entry)
    - `ui/controller.py` (publish `UI_GRAPH_*`)
    - `core/events/topics.py` (add `UI_GRAPH_*`)
    - `ui/views/world_model/knowledge_graph_panel.py` (add full-graph layout and search/filter callbacks if needed)
    - `ui/views/relationship_view.py` (expose reusable edge renderer)
  - New:
    - `ui/views/graph_workspace_view.py`
    - `tests/ui/views/test_graph_workspace_view.py`
- **Acceptance:** full graph renders all nodes/edges; filters and search work; double-click navigates; inspector shows selected node.
- **Risk:** High. **Size:** Large.

---

#### PR-UI-E13 — Insights Placeholder

- **Purpose:** Reserve the `insights` workspace for Phase 10+ with a stub view, sidebar entry, topics, and state file.
- **Files:**
  - Modify:
    - `ui/shell/view_manager.py` (register `insights`)
    - `ui/components/sidebar.py` (add `insights` entry)
    - `core/events/topics.py` (add `UI_INSIGHTS_*`)
    - `core/app_state.py` (add `insights_state` reducer)
  - New:
    - `ui/views/insights_view.py`
    - `core/state/insights_state.py`
    - `tests/ui/views/test_insights_view.py`
- **Acceptance:** `insights` view registered, reachable from sidebar, shows Phase 10 placeholder.
- **Risk:** Low. **Size:** Small.

---

## 7. Hot spots and risks

| # | Risk | Affected PRs | Severity | Probability | Mitigation |
|---|------|--------------|----------|-------------|------------|
| 1 | `core/app_state.py` / `state_applier.py` churn | all | High | High | Land foundation PRs first; make each AppState change additive; isolate reducers. |
| 2 | `application_shell.py` layout conflicts across context bar, palette, and sidebar | E00–E04 | High | Medium | Strict sequential order E02 → E03 → E04. |
| 3 | Second graph engine (`WorldGraphCanvas`) violates canon | E08, E12 | High | Medium | Reuse `BaseGraphCanvas` and `KnowledgeGraphPanel`; code-review for any new canvas class. |
| 4 | Parallel timeline engine violates canon | E09, E11 | High | Medium | Use `TimelineRenderer` + `ExecutionTimelineDock`; reject any new `run_timeline` renderer. |
| 5 | `SelectionInspectorPanel` becomes a third inspector OS | E08 | High | Medium | Host its content in `InspectorHost`/`InspectorDock` by composition. |
| 6 | `home_view.py` removal/merge loses dashboard stats | E00 | Medium | Medium | Port unique `HomeView` widgets into `CommandCenterView`; redirect `home` → `command_center`. |
| 7 | Headless test gap (x86_64 Linux CI cannot launch GUI) | all | Medium | High | Increase `tests/ui/` unit tests; run `APPDATA=/tmp/aicc_appdata python3 -m pytest -m "not slow"`; manual Windows-ARM64 smoke. |
| 8 | Treating existing panel packages as greenfield | E07–E09 | High | Medium | PR descriptions must state “evolve package X” and list only additive/modify files. |
| 9 | Evidence workspace depends on `OrchestrationRunSnapshot.run_history` truth fields | E10 | Medium | Medium | Verify `truth_boundary` publishes snapshotable results; add `EvidenceState` reducer as fallback. |
| 10 | 13 PRs create schedule/scope creep | all | High | High | Use feature flags; ship foundation first; stub new views and fill incrementally. |

---

## 8. Verification

After each evolution PR:

```bash
python3 -m pytest -m "not slow"
python3 -m ruff check ai_command_center
python3 scripts/verify_constitution.py
python3 scripts/verify_ui_constitution.py
```

For palette/inspector/workspace PRs, also run:

```bash
python3 -m pytest tests/ui/
```

---

## 9. Constitutional pre-flight

Before any implementation:

1. **Constitution:** `PROJECT_CONSTITUTION_V4.md` — ownership flow `UI → AppState → EventBus → Services → Repositories → Storage` is unchanged.
2. **Architecture:** `docs/ARCHITECTURE.md` and `docs/ARCHITECTURE_ENFORCEMENT.md` — UI is renderer-only; no direct service/repository calls.
3. **Contracts:** `ai_command_center/core/events/topics.py` and `ai_command_center/core/contracts.py` — new UI topics must be canonical.
4. **Canon:** `docs/audits/REPOSITORY_TRUTH_CANON.md` — baseline is `origin/main`; `phase-11a-command-center` is not SoT.

---

## 10. Summary

`origin/main` already contains the Phase 11 workspace shells and panel packages (`goal_dashboard`, `agent_monitor`, `execution_center`, `world_model`) and the shared primitives (`BaseGraphCanvas`, `TimelineRenderer`, `ExecutionTimelineDock`, `InspectorHost`). Phase B is therefore an **evolution**, not a rewrite:

1. Align on `origin/main` and close stale `phase-11a-command-center` assumptions.
2. Extend the universal inspector and reconcile `SelectionInspectorPanel` by composition.
3. Add the Global Context Bar and OS Palette.
4. Reorganize navigation.
5. Harden each Workspace OS view incrementally (Memory, Brain, Goal, Agent, Execution, World, Evidence, Operations, Graph, Insights).

This reduces risk, reuses the existing UI Constitution and `StateApplierMixin` patterns, and avoids duplicate implementation.
