# Agents Soft-Shadow Inventory (State Authority)

**Status:** ACTIVE — Stage 2 closeout + **SA.mutate remain-outside (ADR-017)**  
**Authority:** `STATE_AUTHORITY_CONTRACT.md`, ADR-006, ADR-013, ADR-017  
**Date:** 2026-08-04  
**Baseline:** ADR-017 acceptance tip

## Verdict

Live agent orchestration is **`AgentRuntimeService`** (factory-registered).  
**`AgentCoordinator`** is Phase-9 research-only (**ADR-013**). State Authority does
**not** own agent pipeline state. Agent runtime memory is largely **ephemeral**.
**No silent-merge** into SA mutate. **No SA.mutate for agents** in this closeout.

| Path | Stack | On SA path? | Disposition |
|------|-------|:-----------:|-------------|
| **A — Live agent runtime** | `AgentRuntimeService` on EventBus (spawn/plan/tool observe) | ❌ (ephemeral) | **keep** — live multi-agent / demo pipelines |
| **B — Research dual** | `AgentCoordinator` (+ related orchestration.agents) | ❌ | **RETIRED from live (ADR-013)** — tests/research only |

---

## Path A — Live

```text
UI / EA / chat hooks
  → AgentRuntimeService topics (spawn, task, cancel, tool observe)
  → ExecutionOrchestrator / tools
  → AppState agent projections
```

Factory: `AgentRuntimeService(bus)` registered as `"agent_runtime"`.

---

## Path B — Research (not live)

`orchestration/agents/agent_coordinator.py` and related modules are **not** in
`service_factory`. Unit/orchestration tests may construct them directly.

---

## State Authority today

| Capability | Agents |
|------------|--------|
| Query aggregate | ❌ no agent_lookup |
| Mutate | ❌ unsupported (**ADR-017** — remain outside) |
| WM overlap | Agent actions may create WM nodes via other services — not agent SoT |

---

## Migration plan

| Step | Action | Gate |
|------|--------|------|
| **A ✅** | Inventory + pins + ADR-013 | Soft-shadow closeout |
| **B ✅** | **Remain outside `SA.mutate`** (no agent pipeline mutate via SA) | **ADR-017** |
| C | Optional SA read-only “active agents” projection from AppState/bus | Later ADR |
| ❌ | Wire AgentCoordinator onto live bus | Forbidden without new ADR |
| ❌ | SA.mutate agent pipeline state without superseding ADR | Forbidden |

---

## References

- `docs/architecture/adr/ADR-013_PLANNING_AGENT_COORDINATOR_DISPOSITION.md`  
- `docs/architecture/adr/ADR-017_SA_MUTATE_WORKFLOWS_EXECUTIONS_AGENTS_DISPOSITION.md`  
- `docs/architecture/SHADOW_SOT_INVENTORY.md`  
- `ai_command_center/services/agent_runtime_service.py`  
- `ai_command_center/orchestration/agents/`  
