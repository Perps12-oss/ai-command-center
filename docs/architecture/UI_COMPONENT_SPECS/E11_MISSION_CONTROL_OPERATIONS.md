# E11 — Mission Control Operations

**Slice:** PR-UI-E11  
**Status:** COMPLETE on `main` (#105) — **not Queue 1**. Historical spec; not pending merge.

## Purpose

New Mission Control Operations workspace: pipeline stage strip, operation roster, and scrubbable timeline that updates the inspector.

## Composition

```
OperationsView
├── Hero (counts, navigate to Evidence/Agents)
├── PipelineStageStrip (Planner→Router→Executor→Verifier→Receipt)
├── OperationCard list (operation_library_index)
└── ExecutionTimelineDock (journal / scrubber events)
```

## State

- Reads `operation_library_index`, `operation_journal`, `active_operation`, `agent_pipeline`, `orchestration_run`, `execution_scrubber`
- No new AppState fields

## Topics

| Topic | Intent |
|-------|--------|
| `ui.operation.select` | Operation focused |
| `ui.operation.scrub` | Timeline scrub |
| `ui.operation.open` | Open operations workspace |

Scrub also publishes `UI_EXECUTION_TIMELINE_SCRUB` (when request_id known) and `UI_INSPECT_SELECT` (`execution_event`).
