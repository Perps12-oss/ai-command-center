# R1 Ungated Docs Closeout — Stop Line

**Date:** 2026-08-04  
**Tip baseline:** `origin/main` @ `426c6b7`

## Ungated queue status

| Track | Status |
|-------|--------|
| Stage 2 soft-shadow (3a–6b + agents) | ✅ closed |
| R1 P1–P4 | ✅ closed |
| R1 P5 Predictive/Undo (ADR-014) | ✅ research-only closed |
| Living-doc honesty (this PR) | ✅ closes remaining ungated docs debt |

## NEXT GATE

**SA.mutate for non-WM domains — requires a new ADR**

Parallel hard stops (do not start without their gates):

| Work | Gate |
|------|------|
| Phase 5 Async EventBus | Performance Investigation Report + human approval |
| Goose / external patterns | Stage 3 + Integration Proposal + ADR |
| Live-wire Predictive/Undo | ADR superseding ADR-014 |
| OperatorKernel / GoalEngine / PlanningEngine / AgentCoordinator re-wire | ADR superseding 006 / 012 / 013 |
| Platform hotkey/tray live wire | Phase 11 / plan dependency (not R1 blocker); optional code PR |

## Optional ungated (not required — separate PRs)

- GoalEngine schema / package cleanup (ADR-012 allows; not R1-blocking)
- Research-tree package deletes (test churn)
