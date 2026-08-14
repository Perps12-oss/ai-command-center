# R1 Ungated / SA.mutate Stop Line

**STATUS:** COMPLETE / CLOSED — not an implementation queue

This stop line is **closed** for R1 / SA.mutate. It is **not** the current planned-work queue.  
Canonical plan: [`docs/governance/IMPLEMENTATION_GUIDE.md`](../governance/IMPLEMENTATION_GUIDE.md) (Queue 1 = [Strategic Runtime Program](../governance/STRATEGIC_RUNTIME_PROGRAM.md)).  
Fossil index: [`docs/governance/HISTORICAL_AND_RETIRED_WORK.md`](../governance/HISTORICAL_AND_RETIRED_WORK.md)

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

## Parallel tracks (superseded as “indefinite gates”)

The table below is **historical R1 wording**. Current disposition is the Strategic Runtime Program:

| Work | Now |
|------|-----|
| Phase 5 EventBus **pool isolation** | **Stream D** — measure first; abandoned branch is not a merge candidate. R4b single-queue remains live until a new ADR. |
| Goose / external patterns | **Stream F** — Gate 1 IP-F; Adopt/Adapt/Reject. Not Goose compatibility. |
| Live-wire Predictive/Undo | ADR superseding ADR-014 — **RETIRED** until then (not a program stream) |
| OperatorKernel / GoalEngine / PlanningEngine / AgentCoordinator re-wire | ADR superseding 006 / 012 / 013 — **RETIRED**; do not restore |
| Platform hotkey/tray | Standalone **macOS Hotkey dropped**. Cross-OS is **Stream G**, last strategic gate. |

## Optional ungated (not required)

- GoalEngine schema / package cleanup (ADR-012 allows)
- Research-tree package deletes
- Memory delete via SA (ADR extending 015)
- Goals lifecycle via SA (ADR extending 016)
- Read-only SA projection of workflow/execution/agent summaries (new ADR)
