# R1 Ungated / SA.mutate Stop Line

**Date:** 2026-08-04  
**Tip baseline:** ADR-017 acceptance (workflows/executions/agents remain outside SA.mutate)

## Ungated / SA.mutate queue status

| Track | Status |
|-------|--------|
| Stage 2 soft-shadow (3a–6b + agents) | ✅ closed |
| R1 P1–P4 | ✅ closed |
| R1 P5 Predictive/Undo (ADR-014) | ✅ research-only closed |
| Living-doc honesty | ✅ closed (#145) |
| ADR-015 Memory `SA.mutate` (`store_memory`) | ✅ closed (#146) |
| ADR-016 Goals `SA.mutate` (`submit_goal`) | ✅ closed (#149) |
| ADR-017 Workflows / Executions / Agents mutate disposition | ✅ **remain outside SA** (this gate) |

## R1 SA.mutate track — CLOSED

Live `SA.mutate` surface:

```text
World Model nodes/edges + store_memory (ADR-015) + submit_goal (ADR-016)
```

Explicitly **out** of SA.mutate (ADR-017): workflows, executions, agents.

No further R1-blocking SA.mutate deepen. Optional extensions need new ADRs and
are **not** required to close this stop line.

## Parallel hard stops (other tracks — not this stop line)

| Work | Gate |
|------|------|
| Phase 5 Async EventBus | Performance Investigation Report + human approval |
| Goose / external patterns | Stage 3 + Integration Proposal + ADR |
| Live-wire Predictive/Undo | ADR superseding ADR-014 |
| OperatorKernel / GoalEngine / PlanningEngine / AgentCoordinator re-wire | ADR superseding 006 / 012 / 013 |
| Platform hotkey/tray live wire | Phase 11 / plan dependency |

## Optional ungated (not required)

- GoalEngine schema / package cleanup (ADR-012 allows)
- Research-tree package deletes
- Memory delete via SA (ADR extending 015)
- Goals lifecycle via SA (ADR extending 016)
- Read-only SA projection of workflow/execution/agent summaries (new ADR)
