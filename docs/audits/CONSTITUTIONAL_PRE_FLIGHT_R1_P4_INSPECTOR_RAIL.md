# Constitutional Pre-Flight — R1 P4 Inspector Rail

**Date:** 2026-08-04  
**Branch:** `cursor/r1-p4-inspector-rail-6855`  
**Baseline:** `origin/main` @ `9be1a29` (#134 Stage 2 closeout + #135 UI freeze)

## Continuity

Stage 2 soft-shadow ungated work is closed. Next ungated R1 work is Priority 4
UI composition residuals.

## In scope

1. Compose World Explorer / Graph Workspace `SelectionInspectorPanel` onto
   `InspectorDock` → `InspectorHost` (single inspector rail).
2. Register Art. 12 selection detail as the `world_node` inspector on that rail.
3. Wire `state_applier` show/clear for those views.
4. Update R1.4 inspector criterion + E08 note.

## Out of scope / gated

- Mission Control `ActivityTimeline` dual (timeline residual — separate PR)
- Async EventBus, Goose, SA.mutate non-WM, OperatorKernel rewire
- GoalEngine schema delete; PlanningEngine/AgentCoordinator wiring

## Invariants

- UI remains renderer-only (AppState / EventBus intents).
- No second inspector OS; WorkspaceOsInspector stays experimental diag.
- Art. 12 field set preserved via payload-backed SelectionInspector.

## Verdict

**GO**
