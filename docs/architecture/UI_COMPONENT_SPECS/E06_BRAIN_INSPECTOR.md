# E06 — Brain Inspector

**Slice:** PR-UI-E06  
**Status:** COMPLETE on `main` — **not Queue 1**.

## Purpose

Dedicated Brain workspace projecting `AppState.brain_state` (kernel, goals, observations, actions, plan).

## Composition

```
BrainView
├── Kernel status
├── GoalCard list
├── ObservationCard list
├── ActionCard list
└── PlanCard
```

## Topics

| Topic | Intent |
|-------|--------|
| `ui.brain.select` | Goal focused from brain |
| `ui.brain.open` | Open brain workspace |
