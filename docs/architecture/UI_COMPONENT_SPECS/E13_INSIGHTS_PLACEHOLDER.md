# E13 — Insights Placeholder

**Slice:** PR-UI-E13  
**Status:** Implemented on feature branch (pending merge)

## Purpose

Reserve the `insights` workspace for Phase 10+ analytics with a stub view, sidebar entry, EventBus intents, and AppState projection.

## Composition

```
InsightsView
├── Hero (title, revision, Refresh / Open Evidence)
└── Body (Article 18 empty-state + insights_state.message)
```

## State

- Field: `AppState.insights_state: InsightsSnapshot`
- Reducer: `reduce_insights_state` handles `UI_INSIGHTS_*`
- No analytics engine in this slice

## Topics

| Topic | Intent |
|-------|--------|
| `ui.insights.open` | Open insights workspace |
| `ui.insights.select` | Focus a future insight id |
| `ui.insights.refresh` | Refresh placeholder projection |

## Acceptance

- `insights` in `VIEW_IDS` and sidebar
- Reachable from command palette / aliases
- Shows informative Phase 10 placeholder (Art. 18), not bare "No Data"
