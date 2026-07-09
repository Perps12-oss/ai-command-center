# TOM — Implementation Audit Report
**Auditor:** Tom, Senior Engineering Auditor (docs/agents/tom-implementation-auditor.json v1.0)
**Scope:** ACC UI Refurbishment — all 7 design items (docs/architecture/ACC_UI_REFURBISHMENT.md)
**Audited revision:** `main` @ `5b25d00` (post PR #49–#55), clean working tree
**Evidence basis:** source code, wiring paths, test runs, governance gates. Claims without code evidence were rejected.

---

## Executive Summary

The UI Refurbishment program is **mid-execution and on-plan**: the two foundational primitives (Chat Workspace shell, Global Inspector System) are genuinely built, wired, AppState-driven, and tested — not mockups. The Provider Dashboard is a wired, pure-display surface. However, the Artifact System has **no domain/service/repository layer** (views run on raw dicts), the Execution Timeline's planned **new `ExecutionEvent` system does not exist** (only the legacy frozen `TimelineEvent` stack, with placeholder `undo()` logic), the Workflow Graph is an **unwired renderer**, and the Automation Workspace has **zero code surface**. All four governance gates pass on main.

**Overall score: 62 / 100 — PARTIALLY_IMPLEMENTED** (as a program; per-item verdicts below). This is consistent with the plan's own sequencing (~PR 8 of 15), so "partial" here means *incomplete*, not *drifted* — no architectural drift or duplicate-primitive violations were found.

---

## Per-Item Verdicts

| # | Design Item | Score | Status | Maturity |
|---|---|---|---|---|
| 1 | Chat Workspace | 92 | COMPLIANT | LEVEL_4 |
| 2 | Global Inspector System | 90 | COMPLIANT | LEVEL_4 |
| 3 | Artifact System | 60 | DEFICIENT (vs end-state; on-plan — PRs 6–7 pending) | LEVEL_2 |
| 4 | Execution Timeline | 48 | DEFICIENT | LEVEL_2 |
| 5 | Provider Dashboard | 84 | PARTIALLY_IMPLEMENTED | LEVEL_4 |
| 6 | Workflow Graph | 35 | NEEDS_REDOING → more precisely NOT WIRED (renderer-only) | LEVEL_1 |
| 7 | Automation Workspace | 0 | NOT STARTED (no code surface) | LEVEL_0 |

---

## Architecture Compliance — PASS

- UI → AppState → EventBus → Services → Repositories boundary holds. All audited views are pure display (no bus/service imports): `chat_workspace_layout.py`, `providers_view.py`, `artifacts_view.py`, `workflow_graph_view.py`.
- Reducers registered centrally (`core/app_state.py:1411-1413`: `_reduce_execution_context`, `_reduce_inspector`); topics canonical in `core/events/topics.py:77-80` (`ui.inspect.select/clear/navigate`).
- Controller publish path intact: `ui/controller.py:175-210` (`publish_inspect_select/clear/navigate`); projection via `ui/shell/state_applier.py:93-110, 269-280`.
- Gates: `ruff` PASS · `arch_lint` PASS (0 new violations) · `verify_constitution` PASS · `UCGS` PASS.
- CustomTkinter-native throughout; no parallel UI system, no external runtime as system of record.

## Primitive Reuse Compliance — PASS (with one debt item)

- **One inspector system**: `InspectorHost` registers `message`/`artifact`/`provider`/`decision` (`inspector_host.py:20-96`) + `execution` in chat (`chat_view.py:252-256`); all payload inspectors share `PayloadInspector` (`payload_inspector.py:16-109`); gestures centralized in `bind_inspect_gestures` (`inspect_gestures.py:1-46`). DecisionCard and ResponseActionStrip route through the same inspect system — no duplicate inspector.
- **One timeline contract**: legacy `TimelineEvent` untouched and frozen; no duplicate log system introduced.
- **Debt:** legacy tab widgets under `ui/views/chat/inspector/` remain (ExecutionInspector feed); `InspectorPanel` removed in PR 11 — `InspectorDock` is the rail shell.

## AppState Compliance — PASS

New UI is AppState-driven (`inspector_state.py:17-69` selection/clear/navigate reducer; navigate map covers all five kinds). State mutations traceable; no hidden local-state duplication found in the new inspector path.

---

## Implementation Findings & Deficiencies

**Item 1 — Chat Workspace (92, COMPLIANT).** 3-pane docked shell wired end-to-end (`chat_view.py:190-256`, `view_manager.py:60-68`, `state_applier.py:93-110`). Tests: 21 passed. Minor: still feature-gated with single-pane fallback (`chat_workspace_layout.py:62-65`) — acceptable, but the flag should have a retirement plan.

**Item 2 — Global Inspector System (90, COMPLIANT).** Full stack exists and is wired: topics, reducer, controller publishes, host + 5 typed inspectors, decision wiring (`decision_card.py:112-117`, `response_action_strip.py:19-62`). Tests: 6 passed, 4 skipped headless (widget tests execute only on Windows CI — verified green on merged PRs). PR 11 adds `InspectorDock`; legacy `InspectorPanel` removed. ExecutionInspector still passes domain objects to legacy tab widgets as dicts (inherited pattern).

**Item 3 — Artifact System (60, DEFICIENT vs end-state).** UI surfaces exist and are wired (`artifacts_view.py`, `artifact_viewer.py`, `state_applier.py:277-280`), and `ArtifactInspector` participates in global inspect. But: **no `domain/artifact.py`, no `artifact_service.py`, no artifact repository, no `artifact_state` slice, no `artifact.created/updated` topics**. `ArtifactsView.apply_state` consumes `list[dict]` — dict-shaped domain data in the view layer violates the domain-dataclass contract. `ArtifactViewer` preview is stubbed for some kinds. No dedicated artifact-domain tests. These are exactly plan PRs 6–7; until they land, the artifact stream is a UI shell over `ExecutionContext.artifacts`.

**Item 4 — Execution Timeline (48, DEFICIENT).** The legacy stack is solid (frozen `TimelineEvent`, SQLite `timeline_repository.py`, `timeline_service.py`, `ExecutionDetailView` with `TimelineRenderer`/`TraceTree`; 13 supporting tests pass). But the plan's core deliverable — a **new append-only `ExecutionEvent` domain + service + `execution_events` table + scrubber + timeline workspace/dock** — has zero code. No timeline view registration, no state projection, no controller publishes, no topics. **Shortcut flag:** `timeline_service.undo()` contains explicit placeholder logic (`timeline_service.py:98-115`) — placeholder presented inside a production service.

**Item 5 — Provider Dashboard (84, PARTIALLY_IMPLEMENTED).** Wired, pure-display, AppState-fed (`providers_view.py`, `state_applier.py:269-271`, reducers at `app_state.py:794-840`), with live monitor / capability matrix / failure explorer subviews and 15 passing tests. `ProviderInspector` exists in the global system. Gaps: `apply_state` accepts loosely-typed generic sequences (`providers_view.py:100-107`); the plan's routing-ribbon/unified-surface design is not evidenced (currently a tabbed layout).

**Item 6 — Workflow Graph (35, renderer-only).** `domain/workflow_graph.py` (NodeState/GraphNode/GraphEdge, linearized `from_workflow_steps`) and a clean canvas renderer exist — but **nothing is wired**: no projector (`WorkflowGraphProjector` — zero matches), no view registration, no state slice, no projection, no controller publishes, no topics, no UI tests. What exists is architecturally clean; verdict reflects absence, not drift. Note the domain builder linearizes step dicts — a real DAG will require rework.

**Item 7 — Automation Workspace (0, NOT STARTED).** No files, symbols, state, topics, registration, or tests. Consistent with plan sequencing (PRs 14–15, blocked on item 6).

## Shortcut Detection Summary

| Flag | Location | Severity |
|---|---|---|
| Placeholder logic in production service | `timeline_service.py:98-115` (`undo()`) | Medium |
| Dicts as domain objects in view layer | `artifacts_view.py` (`list[dict]`), `providers_view.py:100-107`, ExecutionInspector→legacy tabs | Medium |
| Stubbed previews | `artifact_viewer.py:81-124` (some kinds) | Low |
| Unwired UI (dead surface) | `workflow_graph_view.py` | Medium |
| Legacy tab widgets in ExecutionInspector | `inspector_*_tab.py` dict feed | Low |

No fake integrations, no architecture bypasses, no duplicate primitives, no hardcoded workflow behavior found.

---

## Risk Assessment

1. **Highest risk — Execution Timeline (Item 4):** items 3, 6, 7 all depend on timeline integration per the reuse mandate; the new `ExecutionEvent` system being 0% built makes it the critical path. The frozen `TimelineEvent` must not be mutated to shortcut this.
2. **Dict-shaped view contracts** (artifacts/providers) will calcify if PRs 6–7 don't introduce real domain dataclasses before more surfaces consume them.
3. **Legacy inspector tab widgets** — migrate ExecutionInspector dict feed to typed payloads when convenient.
4. **Workflow graph linearization** in the domain builder will need redesign for true DAGs before item 6 wiring starts — cheaper to fix now than after a projector is built on it.

## Next Actions (priority order)

1. **PR 6–7 (Artifact domain/service/state + renderer factory)** — replaces the dict contract; per plan, next in sequence.
2. **PR 8+ (ExecutionEvent domain + service + `execution_events` table)** — and resolve or explicitly ticket the `undo()` placeholder.
3. ~~Schedule the **legacy InspectorPanel removal** PR~~ — done in PR 11 (`InspectorDock`); migrate ExecutionInspector's dict-based tab feed to typed payloads when convenient.
4. Before item 6 wiring: redesign `WorkflowGraph.from_workflow_steps` for non-linear graphs.
5. Type the provider dashboard `apply_state` inputs.

## Final Verdict

| Check | Result |
|---|---|
| Constitution compliance | **PASS** |
| Architecture compliance | **PASS** |
| Primitive reuse compliance | **PASS** |
| CustomTkinter compliance | **PASS** |
| AppState compliance | **PASS** |
| GitHub pattern compliance | **PASS** (patterns adapted, not cloned) |
| Implementation maturity (program) | **LEVEL_2–LEVEL_4 mixed** (items 1/2/5 at L4; 3/4 at L2; 6 at L1; 7 at L0) |
| **Overall status** | **PARTIALLY_IMPLEMENTED — 62/100** |

*Trust code. Verify behavior. Challenge assumptions. Approve only what is actually implemented.* — Tom
