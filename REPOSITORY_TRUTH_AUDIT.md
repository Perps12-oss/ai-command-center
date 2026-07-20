# Repository Truth Audit

**Generated:** 2026-07-20T23:22:21.1358838+01:00
**Repository:** https://github.com/Perps12-oss/ai-command-center.git
**Current branch:** phase-11a-command-center

## goal_dashboard

- **File path:** (none identified)
- **Exists at HEAD:** N/A
- **First file commit:** N/A
- **Commit introducing it:** cb67129 docs: add UI Constitution and Phase 11 frontend implementation plan
- **Branches containing commit:**
  -   cursor/cloud-agent-1784344178346-8nt9j
  - * phase-11a-command-center
  -   phase13-execution-inspector
  -   remotes/origin/cursor/cloud-agent-1784344178346-8nt9j
  -   remotes/origin/phase-11a-command-center
- **Current status:** no file tracked; concept/roadmap reference only
- **Screenshots:** Not applicable (headless environment; no UI executed)
- **Roadmap references:**
  - docs/PHASE_11_FRONTEND_IMPLEMENTATION.md
    - line 35: | **Goal Dashboard** | `brain_state`, `planner_last_plan` | `brain_state.recent_goals`, `brain_state.last_plan`, `planner_last_plan` |
    - line 64: - Active Goal pill (click → Goal Dashboard)
    - line 231: ## Phase 11F — Goal Dashboard
    - line 247: - Workspace Name: "Goal Dashboard"
    - line 313: | 11F | Goal Dashboard | 2 days |

## agent_monitor

- **File path:** (none identified)
- **Exists at HEAD:** N/A
- **First file commit:** N/A
- **Commit introducing it:** cb67129 docs: add UI Constitution and Phase 11 frontend implementation plan
- **Branches containing commit:**
  -   cursor/cloud-agent-1784344178346-8nt9j
  - * phase-11a-command-center
  -   phase13-execution-inspector
  -   remotes/origin/cursor/cloud-agent-1784344178346-8nt9j
  -   remotes/origin/phase-11a-command-center
- **Current status:** no file tracked; concept/roadmap reference only
- **Screenshots:** Not applicable (headless environment; no UI executed)
- **Roadmap references:**
  - docs/PHASE_11_FRONTEND_IMPLEMENTATION.md
    - line 33: | **Agent Monitor** | `agent_pipeline` | `runs`, `active_run_id`, `active_run_ids`, `pipeline_id`, `pipeline_stage`, `planned_tools`, `total_spawned` |
    - line 161: ## Phase 11D — Agent Monitor
    - line 177: - Workspace Name: "Agent Monitor"
    - line 184: - `ai_command_center/ui/views/agent_monitor_view.py` (new)
    - line 311: | 11D | Agent Monitor | 2 days |

## execution_center

- **File path:** (none identified)
- **Exists at HEAD:** N/A
- **First file commit:** N/A
- **Commit introducing it:** cb67129 docs: add UI Constitution and Phase 11 frontend implementation plan
- **Branches containing commit:**
  -   cursor/cloud-agent-1784344178346-8nt9j
  - * phase-11a-command-center
  -   phase13-execution-inspector
  -   remotes/origin/cursor/cloud-agent-1784344178346-8nt9j
  -   remotes/origin/phase-11a-command-center
- **Current status:** no file tracked; concept/roadmap reference only
- **Screenshots:** Not applicable (headless environment; no UI executed)
- **Roadmap references:**
  - docs/PHASE_11_FRONTEND_IMPLEMENTATION.md
    - line 32: | **Execution Center** | `execution_library`, `execution_timeline`, `execution_context`, `orchestration_run` | `active_plan` (steps, status, error), `run_history`, `execution_timeline`, `execution_context.receipt_id`, `orchestration_run.run_history` (truth, receipt) |
    - line 125: ## Phase 11C — Execution Center
    - line 141: - Workspace Name: "Execution Center"
    - line 310: | 11C | Execution Center | 2 days |

## BaseGraphCanvas

- **File path:** (none identified)
- **Exists at HEAD:** N/A
- **First file commit:** N/A
- **Commit introducing it:** (not found in repository history)
- **Branches containing commit:** N/A
- **Current status:** no file tracked; concept/roadmap reference only
- **Also found (related):** GraphCanvas class in ai_command_center/ui/components/graph_canvas.py; first commit: dad6163 feat(ui): PR 12ÔÇô13 WorkflowGraphView + projector + live overlay
- **Screenshots:** Not applicable (headless environment; no UI executed)
- **Roadmap references:**
  - none

## SelectionInspectorPanel

- **File path:** (none identified)
- **Exists at HEAD:** N/A
- **First file commit:** N/A
- **Commit introducing it:** (not found in repository history)
- **Branches containing commit:** N/A
- **Current status:** no file tracked; concept/roadmap reference only
- **Screenshots:** Not applicable (headless environment; no UI executed)
- **Roadmap references:**
  - none

## TimelineRenderer

- **File path:** ai_command_center/ui/components/timeline_renderer.py
- **Exists at HEAD:** True
- **First file commit:** 4d6222ef108ece5c049b485b74a3114d8bb8178e feat(platform): execution observability UI and schema v6 test alignment
- **Commit introducing it:** 4d6222e feat(platform): execution observability UI and schema v6 test alignment
- **Branches containing commit:**
  -   cursor/cloud-agent-1784344178346-8nt9j
  -   feat/program4-slice4-context-plugin-entities
  -   feature/vnext-state-driven-blueprint
  -   main
  - * phase-11a-command-center
  -   phase13-execution-inspector
  -   remotes/origin/cursor/automation-workspace-pr14-15-6c6b
  -   remotes/origin/cursor/cloud-agent-1784344178346-8nt9j
  -   remotes/origin/cursor/execution-event-pr8-6c6b
  -   remotes/origin/cursor/plugin-catalog-entities-6c6b
  -   remotes/origin/cursor/pragmatic-extensibility-docs-7d9d
  -   remotes/origin/cursor/reasoning-loop-pr1-4-b0b8
  -   remotes/origin/cursor/timeline-undo-p1-6c6b
  -   remotes/origin/cursor/ui-backlog-p2-p3-6c6b
  -   remotes/origin/feat/program4-slice4-context-plugin-entities
  -   remotes/origin/feature/p4-workflow-ux-complete
  -   remotes/origin/feature/phase7-ari-update
  -   remotes/origin/feature/planner-evolution-phase-c0-constitution
  -   remotes/origin/feature/vnext-state-driven-blueprint
  -   remotes/origin/main
  -   remotes/origin/phase-11a-command-center
  -   remotes/origin/phase-9-service-registry
  -   remotes/origin/phase13-execution-inspector
- **Current status:** exists at HEAD, clean
- **Screenshots:** Not applicable (headless environment; no UI executed)
- **Roadmap references:**
  - docs/PHASE_11_FRONTEND_IMPLEMENTATION.md
    - line 12: - **No-regression covenant:** `docs/architecture/ACC_UI_REFURBISHMENT.md` — new UI extends existing infrastructure; `TimelineRenderer`, `GraphCanvas`, `InspectorHost`, `WorkflowGraphView`, etc., remain reusable primitives.
  - docs/architecture/ACC_UI_REFURBISHMENT.md
    - line 39: ExecutionTimelineDock   — TimelineRenderer + ExecutionTimelineScrubber
    - line 40: TimelineRenderer        — existing horizontal step tiles (KEEP)
    - line 62: | `TimelineRenderer`, `TraceTree` | `ui/components/` | Extend/compose only |
    - line 195: | `TimelineRenderer` | KEEP |
    - line 201: **`ExecutionTimelineDock`** hosts scrubber + `TimelineRenderer` (scrubber degrades gracefully until PR 9).

## CommandCenterView

- **File path:** ai_command_center/ui/views/command_center_view.py
- **Exists at HEAD:** True
- **First file commit:** 00e9133696fa9f54d6b217e6a87a8eeb3c43f983 feat(phase11a): command center dashboard and top bar
- **Commit introducing it:** 00e9133 feat(phase11a): command center dashboard and top bar
- **Branches containing commit:**
  -   cursor/cloud-agent-1784344178346-8nt9j
  - * phase-11a-command-center
  -   remotes/origin/cursor/cloud-agent-1784344178346-8nt9j
  -   remotes/origin/phase-11a-command-center
- **Current status:** exists at HEAD, clean
- **Screenshots:** Not applicable (headless environment; no UI executed)
- **Roadmap references:**
  - docs/architecture/UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md
    - line 37: | **Command Center dashboard** | New `CommandCenterView` with hero, operations grid, system awareness. | `ui/views/command_center_view.py` |
    - line 56: | 5 | **Brain Inspector workspace** | No dedicated `BrainView`; brain data is only consumed by `TopBar` and `CommandCenterView`. |
    - line 143: | `ui/views/home_view.py` vs `ui/views/command_center_view.py` | `HomeView` is largely superseded by `CommandCenterView`. **Keep `CommandCenterView`**, remove `home` from default nav, and redirect `home` → `command_center`. Port any unique `HomeView` widgets (quick actions, activity feed) into `CommandCenterView`. |

## GoalView

- **File path:** ai_command_center/ui/views/goal_view.py
- **Exists at HEAD:** True
- **First file commit:** f82ed94e98a7c335012ae88c92c1634c144df127 feat(ui): close Phase 11A UI hardening
- **Commit introducing it:** f82ed94 feat(ui): close Phase 11A UI hardening
- **Branches containing commit:**
  -   cursor/cloud-agent-1784344178346-8nt9j
  - * phase-11a-command-center
  -   remotes/origin/cursor/cloud-agent-1784344178346-8nt9j
  -   remotes/origin/phase-11a-command-center
- **Current status:** exists at HEAD, clean
- **Screenshots:** Not applicable (headless environment; no UI executed)
- **Roadmap references:**
  - docs/architecture/UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md
    - line 39: | **New primary workspaces** | `GoalView`, `AgentsView`, `ApprovalsView` registered and wired. | `ui/views/goal_view.py`, `ui/views/agents_view.py`, `ui/views/approvals_view.py`, `ui/shell/view_manager.py` |
    - line 57: | 6 | **Goal Workspace** | `GoalView` is a basic goals list + last plan; missing goal tree, task detail, success criteria, inspector. |
    - line 347: - **Purpose**: Evolve `GoalView` into a full goal operations center with tree, task detail, success criteria, inspector.

## AgentsView

- **File path:** ai_command_center/ui/views/agents_view.py
- **Exists at HEAD:** True
- **First file commit:** f82ed94e98a7c335012ae88c92c1634c144df127 feat(ui): close Phase 11A UI hardening
- **Commit introducing it:** f82ed94 feat(ui): close Phase 11A UI hardening
- **Branches containing commit:**
  -   cursor/cloud-agent-1784344178346-8nt9j
  - * phase-11a-command-center
  -   remotes/origin/cursor/cloud-agent-1784344178346-8nt9j
  -   remotes/origin/phase-11a-command-center
- **Current status:** exists at HEAD, clean
- **Screenshots:** Not applicable (headless environment; no UI executed)
- **Roadmap references:**
  - docs/architecture/UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md
    - line 39: | **New primary workspaces** | `GoalView`, `AgentsView`, `ApprovalsView` registered and wired. | `ui/views/goal_view.py`, `ui/views/agents_view.py`, `ui/views/approvals_view.py`, `ui/shell/view_manager.py` |
    - line 58: | 7 | **Agent Operations Center** | `AgentsView` shows pipeline + run labels; missing run timelines, per-agent detail, inspector. |
    - line 390: - **Purpose**: Evolve `AgentsView` into a mission-control roster with run timelines, pipeline stage, and inspector.

## ApprovalsView

- **File path:** ai_command_center/ui/views/approvals_view.py
- **Exists at HEAD:** True
- **First file commit:** f82ed94e98a7c335012ae88c92c1634c144df127 feat(ui): close Phase 11A UI hardening
- **Commit introducing it:** f82ed94 feat(ui): close Phase 11A UI hardening
- **Branches containing commit:**
  -   cursor/cloud-agent-1784344178346-8nt9j
  - * phase-11a-command-center
  -   remotes/origin/cursor/cloud-agent-1784344178346-8nt9j
  -   remotes/origin/phase-11a-command-center
- **Current status:** exists at HEAD, clean
- **Screenshots:** Not applicable (headless environment; no UI executed)
- **Roadmap references:**
  - docs/architecture/UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md
    - line 39: | **New primary workspaces** | `GoalView`, `AgentsView`, `ApprovalsView` registered and wired. | `ui/views/goal_view.py`, `ui/views/agents_view.py`, `ui/views/approvals_view.py`, `ui/shell/view_manager.py` |

