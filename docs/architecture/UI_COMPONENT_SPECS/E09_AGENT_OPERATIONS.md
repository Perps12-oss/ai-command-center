# E09 — Agent Operations Center

**Slice:** PR-UI-E09  
**Status:** Implemented on feature branch (pending merge)

## Purpose

Evolve `AgentsView` into an Agent Operations Center with active-run cards, pipeline stage, run timeline, and enriched inspector selection — without deleting Phase 11D Agent Monitor panels.

## Composition

```
AgentsView
├── Hero (metrics, contextual cancel → AGENT_CANCEL_REQUEST)
├── Ops strip
│   ├── Active Runs (AgentCard list)
│   ├── PipelineStage
│   └── RunTimeline → TimelineRenderer
└── Phase 11D panels (Pipeline / Active / State / Tasks / History)
```

## State

- Reads `AppState.agent_pipeline` only
- No new AppState fields

## Topics

| Topic | Intent |
|-------|--------|
| `ui.agent.select` | Agent run focused |
| `ui.agent.open` | Open agents workspace |

Selection also publishes `UI_INSPECT_SELECT` kind `agent` with enriched payload.
