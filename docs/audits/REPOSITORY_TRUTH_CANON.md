# Repository Truth Canon — Phase 11 UI Assets

**Status:** Binding verification artifact (Repository Guardian / Tom)  
**Date:** 2026-07-20  
**Authority:** `PROJECT_CONSTITUTION_V4.md` · `docs/governance/PHASE_COMPLETION_RULE.md`  
**Baseline (Source of Truth):** `origin/main` @ `e128a72`

---

## 0. Canon rule

| Rule | Value |
|------|-------|
| Sole code SoT for “what exists” | **`origin/main` tip** |
| Branch tips | Evidence of WIP only — never SoT |
| Phase completion | Features + audits must be on `main` |
| Name collision | Root `REPOSITORY_TRUTH_AUDIT.md` on `phase-11a-command-center` @ `8ba0522` is **non-canonical** |

Any audit that inventories UI assets without checking `origin/main` is **invalid for planning**.

---

## 1. Why Devin’s `8ba0522` audit is wrong

| Fact | Evidence |
|------|----------|
| Devin audited | `phase-11a-command-center` HEAD (`Current branch` in that doc) |
| Divergence at audit time | `origin/main...origin/phase-11a-command-center` = **5 ahead / 13 behind** |
| Commits on `main` absent from that branch | `#76` `423006a`, `#77` `5ae710d`, `#78` `d0bb2ed`, `#79` `811e847`, `#80` `e128a72` |
| False negatives | `goal_dashboard`, `agent_monitor`, `execution_center`, `BaseGraphCanvas`, `SelectionInspectorPanel` are **present on `main`**, absent on `phase-11a` |

Devin correctly observed those paths are missing **on the stale branch**. That does **not** mean they are “concepts only” in the repository.

---

## 2. Canonical inventory (`origin/main` @ `e128a72`)

| Item | Path on `main` | Introduced on `main` | Role |
|------|----------------|----------------------|------|
| `goal_dashboard` | `ai_command_center/ui/views/goal_dashboard/` (7 files) | `811e847` Phase 11 final integration (#79) | Panel package for Goal Dashboard |
| `GoalView` | `ai_command_center/ui/views/goal_view.py` | `423006a` (#76); composes `goal_dashboard` after #79 | Shell — **imports** `goal_dashboard.*` |
| `agent_monitor` | `ai_command_center/ui/views/agent_monitor/` (6 files) | `5ae710d` 11D Agent Monitor (#77) | Panel package for Agent Monitor |
| `AgentsView` | `ai_command_center/ui/views/agents_view.py` | `423006a` (#76); composes `agent_monitor` after #77 | Shell — **imports** `agent_monitor.*` |
| `execution_center` | `ai_command_center/ui/views/execution_center/` (6 files) | `423006a` (#76) | Panel package for Execution Center |
| `ExecutionsView` | `ai_command_center/ui/views/executions_view.py` | (pre-existing + #76 panels) | Shell — **imports** `execution_center.*` |
| `BaseGraphCanvas` | `ai_command_center/ui/components/graph/base_graph_canvas.py` | `d0bb2ed` (#78) | Shared graph engine |
| `GraphCanvas` | `ai_command_center/ui/components/graph_canvas.py` | adapter; subclasses `BaseGraphCanvas` | Workflow adapter only |
| `SelectionInspectorPanel` | `ai_command_center/ui/views/world_model/selection_inspector_panel.py` | `423006a` (#76) | World Model Art. 12 inspector panel |
| `KnowledgeGraphPanel` | `ai_command_center/ui/views/world_model/knowledge_graph_panel.py` | `423006a` (#76) | Projects onto `BaseGraphCanvas` |
| `TimelineRenderer` | `ai_command_center/ui/components/timeline_renderer.py` | `4d6222e` | Timeline primitive |
| `ExecutionTimelineDock` | `ai_command_center/ui/components/docks/execution_timeline_dock.py` | hosts `TimelineRenderer` | Timeline dock |
| `CommandCenterView` | `ai_command_center/ui/views/command_center_view.py` | `423006a` (#76) on `main` | Command Center shell |
| `ApprovalsView` | `ai_command_center/ui/views/approvals_view.py` | `423006a` (#76) | Approval Center shell |
| `InspectorHost` / `InspectorDock` | `ui/components/inspector/inspector_host.py`, `ui/components/docks/inspector_dock.py` | earlier | Universal inspector rail |

### Existence matrix (verified 2026-07-20)

| Path | `origin/main` | `origin/phase-11a-command-center` |
|------|:-------------:|:---------------------------------:|
| `ui/views/goal_dashboard/` | YES | NO |
| `ui/views/agent_monitor/` | YES | NO |
| `ui/views/execution_center/` | YES | NO |
| `ui/components/graph/base_graph_canvas.py` | YES | NO |
| `ui/views/world_model/selection_inspector_panel.py` | YES | NO |
| `ui/views/world_model/knowledge_graph_panel.py` | YES | NO |
| `ui/components/timeline_renderer.py` | YES | YES |
| `ui/views/command_center_view.py` | YES | YES |
| `ui/views/goal_view.py` | YES | YES |
| `ui/views/agents_view.py` | YES | YES |
| `ui/views/approvals_view.py` | YES | YES |

### Class evidence (`git grep` on `origin/main`)

```text
class BaseGraphCanvas          → ui/components/graph/base_graph_canvas.py:21
class SelectionInspectorPanel  → ui/views/world_model/selection_inspector_panel.py:14
class TimelineRenderer         → ui/components/timeline_renderer.py:68
class CommandCenterView        → ui/views/command_center_view.py:25
class GoalView                 → ui/views/goal_view.py:40
class AgentsView               → ui/views/agents_view.py:35
```

---

## 3. Composition model (do not flatten)

Names like `goal_dashboard` are **packages**, not missing files:

```text
GoalView  ──imports──►  ui/views/goal_dashboard/*
AgentsView ──imports──►  ui/views/agent_monitor/*
ExecutionsView ──imports──► ui/views/execution_center/*
WorldExplorerView ──imports──► ui/views/world_model/*
                                 ├── KnowledgeGraphPanel → BaseGraphCanvas
                                 └── SelectionInspectorPanel
GraphCanvas (workflow) ──subclasses──► BaseGraphCanvas
```

Auditing only for `*_view.py` filenames and ignoring packages produces false “concept only” results.

---

## 4. Correction table — Devin `8ba0522` → Canon

| Item | Devin claim (`phase-11a`) | Canon (`origin/main`) |
|------|---------------------------|------------------------|
| `goal_dashboard` | none (concept) | **EXISTS** as package; used by `GoalView` |
| `agent_monitor` | none (concept) | **EXISTS** as package; used by `AgentsView` |
| `execution_center` | none (concept) | **EXISTS** as package; used by `ExecutionsView` |
| `BaseGraphCanvas` | not found | **EXISTS**; shared graph SoT (#78) |
| `SelectionInspectorPanel` | not found | **EXISTS**; World Model panel (#76) |
| `TimelineRenderer` | exists | **EXISTS** (agree) |
| `CommandCenterView` | exists on branch | **EXISTS on main** (via #76; branch first-commit SHAs differ due to history) |
| `GoalView` / `AgentsView` / `ApprovalsView` | exists on branch | **EXISTS on main**; shells compose the packages above |

---

## 5. Prior audit alignment

`docs/audits/REPOSITORY_TRUTH_AUDIT.md` (2026-07-18, baseline `d0bb2ed`) already warned:

- `phase-11a-command-center` was **superseded** → close PR #75; delete branch  
- `BaseGraphCanvas` already on main via #78  
- Remaining 11E/11F gaps were to land via Phase 11 final integration  

Those gaps landed in `#79` (`811e847`). This canon **supersedes** both:

1. The stale sections of the 2026-07-18 audit that still say 11E/11F are missing from main  
2. The non-canonical root audit at `phase-11a` @ `8ba0522`

---

## 6. Binding rules for Phase B (Devin + Cursor)

Until a new plan is written against this canon:

1. **Baseline = `origin/main` only.** Do not plan from `phase-11a-command-center`.  
2. **Mandatory reuse**
   - Graph → `BaseGraphCanvas` (adapters OK; no second engine / no `WorldGraphCanvas` engine)  
   - Timeline → `TimelineRenderer` + `ExecutionTimelineDock` (no parallel `run_timeline` engine)  
   - Inspector → extend `InspectorHost`/`InspectorDock`; reconcile `SelectionInspectorPanel` by composition, not a third inspector OS  
3. **Evolve** `GoalView` / `AgentsView` / `ExecutionsView` / `WorldExplorerView` and their panel packages — do not treat them as greenfield.  
4. **AppState policy** must be stated explicitly (composition-only vs amendment) before coding.  
5. Close or ignore PR #75 as SoT; Phase B PRs branch from `main`.

---

## 7. Reproduction commands

```bash
git fetch origin main phase-11a-command-center
git rev-list --left-right --count origin/main...origin/phase-11a-command-center
# expect: main ahead of phase-11a for Phase 11 merges

for f in \
  ai_command_center/ui/views/goal_dashboard \
  ai_command_center/ui/views/agent_monitor \
  ai_command_center/ui/views/execution_center \
  ai_command_center/ui/components/graph/base_graph_canvas.py \
  ai_command_center/ui/views/world_model/selection_inspector_panel.py
 do
  git cat-file -e "origin/main:$f" && echo "main HAS $f"
  git cat-file -e "origin/phase-11a-command-center:$f" 2>/dev/null || echo "phase-11a LACKS $f"
done

git grep -n 'class BaseGraphCanvas\|class SelectionInspectorPanel' origin/main -- ai_command_center/ui/
```

---

## 8. Guardian verdict

| Question | Result |
|----------|--------|
| Are contested Phase 11 packages real on `main`? | **YES** |
| Is Devin’s “concept only” finding canonical? | **NO — wrong baseline** |
| May Phase B planning proceed from `phase-11a` tip? | **NO** |
| Required next step for Devin | Rewrite evolution roadmap against this canon + `origin/main` |

**Canon status: ESTABLISHED**
