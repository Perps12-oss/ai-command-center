# Constitutional Pre-Flight — ADR-017 SA.mutate Workflows/Executions/Agents Disposition

**Date:** 2026-08-04  
**Branch:** `cursor/adr017-sa-mutate-disposition-6855`  
**Baseline:** `origin/main` @ `c0dd1af` (#149 ADR-016 + #150)

## Continuity

- ADR-015 Memory mutate + ADR-016 Goals submit on `main`
- Stop line next gate: workflows / executions / agents SA.mutate (each needs ADR)
- Soft-shadow inventories **already** keep these domains outside SA mutate
- This PR = **one combined gate**: ADR-017 disposition (remain outside) + honesty docs + pin reinforcement

## Authority read

- [x] Constitution / STATE_AUTHORITY_CONTRACT / ADR-006 / 013 / 015 / 016
- [x] WORKFLOWS / EXECUTIONS / AGENTS soft-shadow inventories
- [x] `R1_UNGATED_STOP_LINE.md`

## Scope (in)

- ADR-017 Accepted: workflows, executions, and agents **remain outside** `SA.mutate`
- Close inventory deferred steps (5c/6c/agent mutate) as disposition, not as live wire
- Update stop line: **R1 SA.mutate track CLOSED**
- Keep / reinforce unsupported-op pin tests

## Out of scope (hard)

- Implementing `start_workflow` / execution append / agent spawn via SA
- Silent-merge of workflow_runs ↔ execution_runs ↔ WM
- Wiring AgentCoordinator (ADR-013)
- Async EventBus / Goose / Predictive-Undo / OperatorKernel
- Optional GoalEngine cleanup / memory delete / goals lifecycle

## Why disposition (not mutate)

| Domain | Why SA.mutate would dual-write or break ownership |
|--------|-----------------------------------------------------|
| Workflows | Live SoT = Engine + Persistence; 5b kept execution-scoped; no SA lookup |
| Executions | Append-only diagnostic SoT; mutate would invent a second writer |
| Agents | Ephemeral `AgentRuntimeService`; Coordinator research-only (ADR-013) |

## Verdict

**GO**
