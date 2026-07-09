# ACC UI Refurbishment — Implementation Plan (ARCHIVED)

**Status:** COMPLETE — PR 1–15 + polish merged to `main` @ `35bed6e` (Jul 2026)  
**Active follow-on:** [UI_REFURBISHMENT_BACKLOG.md](../UI_REFURBISHMENT_BACKLOG.md)  
**Related:** [CHAT_MODERNIZATION_SPEC.md](../CHAT_MODERNIZATION_SPEC.md), [WORKFLOW_ENGINE.md](../WORKFLOW_ENGINE.md), [PROVIDER_PLATFORM.md](../PROVIDER_PLATFORM.md), [PROGRAM4_GATE_STATUS.md](../PROGRAM4_GATE_STATUS.md)

> Retained for architectural constraints (no-regression covenant, naming rules).
> Do not treat as an active implementation checklist.

---

## Strategic frame

ACC evolves along four questions on every surface:

- **What is running?** → execution status, live graphs
- **What happened?** → timeline, trace tree, receipts
- **What was produced?** → artifacts, drafts, versions
- **What can act next?** → approvals, capability actions

Technology boundary: **CustomTkinter desktop only**. Open WebUI, LibreChat, Langflow, n8n, Grafana, Temporal, and Airflow are **UX/IA references**, not embedded runtimes.

---

## Design Item roadmap

```text
1. Chat Workspace          (scaffold landed; wiring pending)
2. Inspector System        ← first reusable UI primitive
3. Artifact System
4. Execution Timeline
5. Provider Dashboard      (parallel track — see PROVIDER_PLATFORM.md)
6. Workflow Graph
7. Automation Workspace
```

### Architecture layers

```text
Primitive Layer (Design Items #2 + #4)
  InspectorHost           — registry + type inspectors
  InspectorDock           — embeds InspectorHost in any workspace rail
  ExecutionTimelineDock   — TimelineRenderer + ExecutionTimelineScrubber
  TimelineRenderer        — existing horizontal step tiles (KEEP)

Workspace Layer (Design Items #1, #3, #5–#7)
  Chat Workspace | Artifact System | Provider Dashboard
  Workflow Graph (Slice 1) | Automation Workspace (Slice 2)
```

---

## No-regression covenant

New UI work **extends** existing infrastructure; it does not replace or break it.

| Asset | Location | Rule |
|-------|----------|------|
| `ExecutionRun` | `domain/execution_run.py`, `execution_run_repository.py` | Append-only; never overwrite rows |
| `ReplayRunner` | `orchestration/replay/replay_runner.py` | Keep API; timeline UI is a projection |
| `TracingService` | `telemetry/tracing_service.py` | Keep OTel bridge |
| `TraceSpan` | `domain/trace_span.py` | Keep tree builder |
| `Execution` | `domain/execution.py` | Keep; no parallel minimal class |
| **Frozen** `TimelineEvent` | `core/timeline/timeline_event.py` | DO NOT MODIFY — separate from `ExecutionEvent` |
| `WorkflowGraphView` | `ui/views/workflow_graph_view.py` | Keep canvas; expand layout around it |
| `TimelineRenderer`, `TraceTree` | `ui/components/` | Extend/compose only |
| `ExecutionsView`, `ExecutionDetailView` | `ui/views/` | Keep; enhance with scrubber |
| `WorkflowPersistenceService` | `services/` | Keep; feeds execution events |
| Production `ChatView` | `FEATURE_DOCKING` gates 3-pane | Legacy path until flag on |
| Tests | `test_workflow_persistence.py`, `test_ui_queue.py`, etc. | Must pass after every PR |

**Naming:** `TimelineEvent` (workspace audit) ≠ `ExecutionEvent` (execution replay).

---

## Constitutional constraints

| Rule | Implication |
|------|-------------|
| UI isolation | Views read **AppState** only; publish via **UIController → EventBus** |
| No global state in UI | Session metadata flows through repositories over time |
| CustomTkinter stays | Port patterns; do not embed web stacks |
| Host platform supremacy | ACC orchestration/provider stack is authoritative |

---

## Design Item #1 — Chat Workspace

Three-pane shell (18% / 62% / 20%): `ConversationList` | message feed + composer | `InspectorHost`.

**Scaffold (exists, wiring pending):**

- `ui/views/chat/chat_workspace_layout.py` — `ChatWorkspaceLayout`
- `ui/views/chat/conversation_list.py`, `chat_header.py`, `conversation_metadata.py`
- Gate: `Feature.FEATURE_DOCKING`

**Tickets:** wire layout into `chat_view.py` + `StateApplierMixin`; message blocks; composer; tool/artifact cards.

**Reference mapping:** Open WebUI (left rail IA), LibreChat (message blocks), Langflow (inspector inspiration).

---

## Design Item #2 — Global Inspector System

**Goal:** Every ACC object inspectable via one panel — click → context without navigation.

**Layout:** Permanent right panel (320–420px), resizable, collapsible:

```text
Navigation | Workspace | Inspector
```

**Architecture:**

```python
InspectorHost          # shell: header, collapse, resize, registry
MessageInspector       # registered dynamically
ExecutionInspector
ArtifactInspector
ProviderInspector
DecisionInspector      # ACC-unique
```

Do **not** hardcode per-surface inspector panels. Existing tab modules (`inspector_trace_tab.py`, etc.) become **sections inside `ExecutionInspector`**, not top-level tabs.

**Interaction rules:**

| Gesture | Behavior |
|---------|----------|
| Single click | Open/update Inspector (`ui.inspect.select`) |
| Double click | Navigate to workspace (`ui.inspect.navigate`) |

**Backend seams:**

- `domain/inspectable.py` — `InspectableRef(kind, id, payload_ref)`
- `core/state/inspector_state.py` — AppState reducer
- `domain/decision.py` — reason, alternatives, chosen, affected files
- Topics: `ui.inspect.select`, `ui.inspect.clear`, `ui.inspect.navigate`

**`InspectorDock`** (used by Workflow Graph, Automation, Provider): layout shell that **hosts `InspectorHost`**, not raw `InspectorPanel`.

---

## Design Item #3 — Artifact System

Chat becomes an **artifact stream UI**: Execution → Artifact → Inspector → Decision.

### CustomTkinter components

| Component | Path | Notes |
|-----------|------|-------|
| `ArtifactCard` | `ui/views/chat/artifact_card.py` | Refactor: Header, Preview, ExecutionBadge, Actions |
| `ArtifactViewer` | `ui/components/artifact_viewer.py` | `compact` (Inspector) / `full` (Workspace) |
| `ExecutionBadge` | `ui/components/execution_badge.py` | NEW — clickable → Inspector |
| `ArtifactListView` | `ui/components/artifact_list_view.py` | NEW — workspace + inspector |
| `ArtifactRendererFactory` | `ui/renderers/` | text, code, image, execution, decision renderers |

### Domain + services

- `domain/artifact.py` — `Artifact`, `ArtifactType`
- `domain/decision.py` — shared with DecisionInspector
- `services/artifact_service.py` — bus only; calls `ArtifactRepository`
- `core/state/artifact_state.py` — `recent_artifacts` projection
- Topics: `artifact.created`, `artifact.updated`, `ui.artifact.action` (exists)

**Event flow:** `execution.completed` → `artifact.created` → AppState → `ArtifactCard` in chat → `ArtifactInspector` sync if selected.

---

## Design Item #4 — Execution Timeline

Convergence layer: EventStore (append-only) + Temporal (workflow steps) + OpenTelemetry (causality) + Redux DevTools (UI scrubber). **Port patterns only** — SQLite + EventBus implementation.

### `ExecutionEvent` domain (NEW)

```python
@dataclass(frozen=True)
class ExecutionEvent:
    event_id: str
    trace_id: str
    parent_event_id: str | None
    timestamp: float
    event_type: str
    actor: str
    scope: str
    request_id: str
    payload: tuple[tuple[str, str], ...]
    state_diff: tuple[tuple[str, str], ...] | None
```

- `ExecutionEventService` subscribes to existing bus topics; **appends** rows
- `execution_events` SQLite table (NEW) alongside existing `execution_runs`
- `ReplayRunner.build_timeline()` **kept** — fallback when event stream empty

### UI (extend existing)

| Widget | Action |
|--------|--------|
| `TimelineRenderer` | KEEP |
| `ExecutionTimelineScrubber` | NEW — event index pointer |
| `TraceTree` | KEEP — causality expansion |
| `ExecutionDetailView` | Enhance with scrubber |
| `ExecutionTimelineView` | NEW workspace page |

**`ExecutionTimelineDock`** hosts scrubber + `TimelineRenderer` (scrubber degrades gracefully until PR 9).

---

## Design Item #5 — Provider Dashboard

Mission-control surface for provider health, latency, errors, live requests. Reuses `ProviderInspector`, `provider_health_map`, `ExecutionEvent` aggregates. Full spec: [PROVIDER_PLATFORM.md](PROVIDER_PLATFORM.md). **Does not block Workflow Graph.**

---

## Workflow Graph + Automation Workspace — UI Plan

### Design Item #6 — Workflow Graph (Slice 1)

**Why first:** Automation without a graph model is an empty ops console. Graph UI **composes** Inspector + Timeline primitives.

**References (pattern only):** n8n (layout), Langflow (node categories), Node-RED (palette→canvas), Airflow (node state colors).

```text
┌─────────────────────────────────────────────────────────┐
│ WorkflowToolbar  [workflow name] [Run] [Compare]        │
├──────────────┬──────────────────────────────────────────┤
│ NodeLibrary  │           GraphCanvas                    │
├──────────────┴────────────────────┬─────────────────────┤
│ ExecutionTimelineDock             │ InspectorDock       │
└───────────────────────────────────┴─────────────────────┘
```

**Backend (projection only — no new engine):**

- `WorkflowGraphProjector` — `workflow_runs` + `agent_pipeline_*` → `WorkflowGraph`
- `core/state/workflow_graph_state.py` — `active_graph`, `selected_node_id`
- UI topics: `ui.workflow.node.select`, `ui.workflow.run` → `workflow.start`

**Node library (Slice 1 static):** Planning | Providers | Tools | Artifacts | Inspectors | Automation | Memory | External

**Slice 1 acceptance:** library + canvas + bottom docks; node select updates inspector; run triggers linear workflow via bus; projector tests green.

**Out of scope Slice 1:** full DnD, branching, persisted YAML, `RetryVisualization` / `ApprovalNode` (Slice 1b).

### Design Item #7 — Automation Workspace (Slice 2)

**Blocked on:** Slice 1 + persistable workflow definition.

```text
AutomationWorkspaceView
├── AutomationCatalog      (Activepieces-style cards)
├── ActiveRunsPanel        (Trigger.dev live progress)
├── ScheduleManager        (n8n cron rows)
├── FailureQueue           → ExecutionTimelineDock + InspectorDock
├── TemplateGallery
└── InspectorDock
```

References: n8n (schedules), Activepieces (catalog), Trigger.dev (active runs).

---

## PR sequence

| PR | Scope |
|----|-------|
| 1 | Chat workspace wiring (layout + conversation list + header) |
| 2 | InspectorHost + MessageInspector + inspector_state |
| 3 | ExecutionInspector + expandable sections |
| 4 | ArtifactInspector + ProviderInspector + interaction rules |
| 5 | DecisionInspector + response action strip |
| 6 | Artifact domain + repository + service + artifact_state |
| 7 | ArtifactCard v2 + ArtifactViewer + renderer factory |
| 8 | ExecutionEvent domain + repository + service |
| 9 | Scrubber + ExecutionDetailView + ReplayRunner fallback |
| 10 | ExecutionTimelineView + ExecutionInspector timeline |
| (parallel) | Provider Dashboard |
| 11 | InspectorDock + ExecutionTimelineDock |
| 12 | WorkflowGraphView n8n layout + projector + nav |
| 13 | Node select/run + live overlay + tests |
| 14–15 | Automation Workspace Slice 2 |

---

## Testing strategy

| Layer | Approach |
|-------|----------|
| Headless | pytest for services, reducers, `ReplayRunner`, `WorkflowGraphProjector` |
| UI | Widget smoke tests with `APPDATA` set |
| Manual | Windows ARM64 — 3-pane chat, inspector, workflow graph |
| Architecture | `python tools/ucgs_runner.py`; `scripts/arch_lint.py` |

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Tab-based `InspectorPanel` diverges | Refactor to `InspectorHost` in PR 2 |
| Conflate `TimelineEvent` / `ExecutionEvent` | Separate frozen contracts |
| Legacy execution data | `ReplayRunner` fallback; regression tests |
| Import EventStoreDB/Temporal/Redux | Pattern references only |
| CTk lacks native docking | `PanedWindow` + ratios |
