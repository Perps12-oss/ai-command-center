# ADR-017: Workflows / Executions / Agents — SA.mutate Disposition

**Status:** Accepted — **remain outside State Authority mutate**  
**Date:** 2026-08-04  
**Deciders:** Product / architecture (close R1 SA.mutate stop-line gate)  
**Does not supersede:** ADR-005, ADR-006, ADR-013, ADR-015, ADR-016  
**Related:** soft-shadow inventories 5a–5b / 6a–6b / Agents; `R1_UNGATED_STOP_LINE.md`  
**Baseline:** `origin/main` @ `c0dd1af`

---

## Context

After ADR-015 (Memory `store_memory`) and ADR-016 (Goals `submit_goal`), the
R1 stop line still listed **workflows / executions / agents** as needing ADRs
before any `SA.mutate` deepen.

Stage 2 soft-shadow inventories already recommended keeping them outside SA:

| Domain | Inventory verdict |
|--------|-------------------|
| Workflows | **5b** — keep execution-scoped; no `workflow_lookup` / SA project hooks |
| Executions | **6a+6b** — append-only diagnostic SoT; correlate via `correlation_id` only |
| Agents | Live = ephemeral `AgentRuntimeService`; Coordinator **RETIRED from live (ADR-013)** |

Wiring mutate for these domains would create the same class of split-brain
ADR-006/012/013 rejected elsewhere: dual run writers, dual append paths, or
SA owning ephemeral pipeline state.

---

## Decision

**Accepted: Workflows, Executions, and Agents remain outside `SA.mutate`.**

Binding rules:

1. **Do not** add `start_workflow` / `complete_workflow` / similar ops to
   `StateAuthorityService.mutate`.
2. **Do not** add execution append / patch / delete ops to `SA.mutate`
   (diagnostic tables stay append-only via Execution* services).
3. **Do not** add agent spawn / cancel / pipeline ops to `SA.mutate`.
4. **Do not** silent-merge `workflow_runs` ↔ `execution_runs` ↔ World Model.
5. **Do not** wire `AgentCoordinator` onto live intake (ADR-013 stands).
6. Optional later **read-only** SA projection of recent runs / active agents
   requires a **new ADR** / contract slice — not implied by this disposition.
7. Promotion of any of these domains onto `SA.mutate` requires a **new ADR**
   that proves a single SoT callback (ADR-015/016 pattern) without dual-writers.

Live paths remain:

```text
Workflows:  WORKFLOW_START → WorkflowEngine → Persistence → AppState
Executions: ExecutionRun/Event/Query services → repos (append-only)
Agents:     AgentRuntimeService (ephemeral) → AppState projections
SA.mutate:  WM nodes/edges + store_memory + submit_goal only
```

---

## Consequences

| Area | Effect |
|------|--------|
| R1 SA.mutate stop line | **CLOSED** for non-WM deepen track |
| Soft-shadow 5c / 6c / agent mutate | Disposition closed — remain outside |
| Truth matrix | Workflows/executions/agents mutate = **out of SA** (Accepted) |
| Pin tests | Unsupported-op tests remain mandatory |

---

## Out of scope

- Implementing mutate for these domains  
- Async EventBus / Goose / Predictive-Undo / OperatorKernel re-wire  
- GoalEngine schema cleanup / memory delete / goals lifecycle via SA  

---

## Verification

| Check | How |
|-------|-----|
| Unsupported ops | Soft-shadow pin tests reject workflow / execution / agent mutate ops |
| SA supported set | Only WM + `store_memory` + `submit_goal` |
| No factory hooks | No `workflow_lookup` / execution_lookup / agent_lookup mutate callbacks |
| Docs | Stop line + inventories + contract + matrix updated |

---

## References

- `docs/architecture/state_authority/WORKFLOWS_SOFT_SHADOW_INVENTORY.md`  
- `docs/architecture/state_authority/EXECUTIONS_SOFT_SHADOW_INVENTORY.md`  
- `docs/architecture/state_authority/AGENTS_SOFT_SHADOW_INVENTORY.md`  
- `docs/architecture/adr/ADR-013_PLANNING_AGENT_COORDINATOR_DISPOSITION.md`  
- `docs/architecture/adr/ADR-015_STATE_AUTHORITY_MUTATE_MEMORY.md`  
- `docs/architecture/adr/ADR-016_STATE_AUTHORITY_MUTATE_GOALS.md`  
- `docs/audits/R1_UNGATED_STOP_LINE.md`  
- `tests/test_workflows_sa_soft_shadow.py`  
- `tests/test_executions_sa_soft_shadow.py`  
- `tests/test_agents_sa_soft_shadow.py`  
