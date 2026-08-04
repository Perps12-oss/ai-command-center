# State Authority Contract

**Status:** ACTIVE (soft-shadow Stage 2 closed; Memory mutate via ADR-015; other non-WM mutate ADR-gated)  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `ADR-005_WORLD_MODEL_AUTHORITY.md`, `ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`, `ADR-015_STATE_AUTHORITY_MUTATE_MEMORY.md`  
**Verified:** ADR-015 acceptance tip (2026-08-04)  
**Implementation today:** `ai_command_center/services/state_authority_service.py`  
**Domain types:** `ai_command_center/domain/state_authority.py` (`StateQuery`, `StateProjection`, `StateDelta`, `MutationReceipt`, `ProjectionScope`)  
**Milestone:** PHASE R1 Priority 3 / Stage 2 (soft-shadow closed; WM + Memory `store_memory` mutate live)  
**Stop line:** `docs/audits/R1_UNGATED_STOP_LINE.md`

---

## Why this exists

ACC has a **canonical execution path** (ADR-006). Soft-shadow inventories for
Goals / Memory / Workflows / Executions / Agents are closed. Memory writes may
use **`SA.mutate(store_memory)`** (ADR-015). Remaining maturity gap:
**goals / workflows / executions / agents mutate** — each still ADR-gated.

Without this contract, services and UI invent parallel “truth”:
- World Model mutations without a receipt
- Planner reading AppState or SQLite directly
- Goals / workflows silently dual-writing

```text
Execution ownership  → mostly solved (ExecutionAuthority chain)
State ownership      → soft-shadow closed; WM + Memory store_memory mutate live
```

State Authority is **not** a giant god-service. It is a **contract** — the only approved way to **query**, **mutate**, and **project** workspace reality.

---

## Architectural position

### Target flow (Workspace OS)

```text
Workspace Reality
      ↓
State Authority          ← query / mutate / project (this contract)
      ↓
Context Projection
      ↓
Planner                  ← planner sits AFTER state, not before
      ↓
Execution (ExecutionAuthority → Orchestrator)
      ↓
State Mutation (+ receipt)
      ↓
Projection Update (AppState)
      ↓
UI
```

### Inversion required

| Wrong (chat-era) | Right (workspace OS) |
|------------------|----------------------|
| Text → Planner → maybe peek at stores | State query → Context → Planner → Execute → Mutate state |

---

## Contract (logical interface)

Implementations may be Python protocols / services; the contract is behavioral.

```python
# Logical contract — not necessarily a single class file.

class StateAuthority:
    def query(self, query: StateQuery) -> StateProjection:
        """Read authoritative workspace reality for a scope. No side effects."""

    def mutate(self, delta: StateDelta) -> MutationReceipt:
        """Apply an authoritative state change. Returns receipt for truth/evidence."""

    def project(self, scope: ProjectionScope) -> UIProjection:
        """Build decision or UI-facing projection from authoritative stores."""
```

### Callers

| Caller | May use State Authority for |
|--------|----------------------------|
| `ExecutionAuthorityService` | Pre-decision `query` / `project` before plan dispatch |
| `PlannerService` | Context snippets derived from state — never direct repo access |
| `OrchestrationService` | Post-execution mutation verification |
| UI | **Never** — UI reads `AppState` only |
| Services | **Never** direct authoritative store access outside this contract |

### Backing systems (aggregated, not bypassed)

**Ownership table — PUBLISHED (R1.3)** — verified on `main` 2026-07-30.

State Authority **may aggregate** internally; callers must not care which store backs a projection:

| Domain | Current backing (evidence on `main`) | Authoritative? | Stage 2 disposition |
|--------|--------------------------------------|----------------|---------------------|
| World Model | `WorldModel` + SQLite repo | ✅ primary (ADR-005) | Aggregate via `query` / `project` |
| Goals | `GoalRepository` + `SingleGoalScheduler` (live); `GoalEngine` **RETIRED (ADR-012 A)** | ✅ live / ❌ Phase-9 | Live via `goal_lookup`; Phase-9 off product path — see `SHADOW_SOT_INVENTORY.md` / ADR-012 |
| Memory | `MemoryGraphService` | ✅ SA lookup + Assembler 4b; **SA.mutate `store_memory` (ADR-015 / 4d)**; tools soft dual (4c) | Same SoT; no silent merge with WM |
| Timeline / executions | `ExecutionRunRepository`, events | ✅ 6a+6b append-only + correlation | Keep append-only outside SA mutate |
| Workflows | `WorkflowRunRepository` (+ Engine/Persistence) | ✅ 5a+5b execution-scoped | Keep outside SA; mutate deferred (ADR) |
| Agent runtime | `AgentRuntimeService` pipeline state | ⚠️ partial | Inventory; no silent merge |
| UI | `AppState` | projection only — **never** authoritative | Unchanged |

**Objective:** one authoritative access layer — not “move everything into World Model overnight,” but **no durable truth outside the contract**.

### Event topics (State Authority)

| Topic | Role |
|-------|------|
| `state.context.built` | Published after successful `query` / `project` |
| `state.context.request` / `state.context.result` | Reserved bus pair — not yet consumed |
| `workspace.active` / `workspace.deactivated` | SA tracks active workspace for default scope |
| `runtime.action.request` → BrainRuntime → WM | Parallel interim path for orchestration (still valid) |
| `world_model.mutation.applied` | Published by SA after successful `mutate()` node ops |

---

## Rules

### R1 — Single access path

No subsystem may maintain **authoritative** state outside State Authority.

Transient execution caches and rebuildable projections are allowed. Durable workspace truth is not.

### R2 — Planner consumes state, not chat

Planner inputs must include `StateProjection` (or `StateContext` successor) from State Authority. Chat history is optional context, never the sole source of workspace truth.

### R3 — Mutations are receipted

Every authoritative mutation returns a `MutationReceipt` correlatable with execution receipts and truth validation.

### R4 — UI is projection-only

```text
State Authority → AppState reducers → UI
```

Forbidden: UI or services reading SQLite / repos directly for authoritative decisions.

### R5 — Reconstruction without conversation

The system must be able to reconstruct workspace reality after deleting all chat sessions (see ADR-006 acceptance test).

---

## Current implementation gap (honest baseline)

| Capability | Today on `main` (post Slice 1) | Contract target |
|------------|--------------------------------|-----------------|
| `StateAuthorityService.project()` | ✅ wired into ExecutionAuthority; delegates to `query` | Keep; extend |
| `query()` with structured `StateQuery` | ✅ Stage 2 Slice 1 | Keep; deepen filters |
| `mutate()` with `StateDelta` | ✅ WM node + edge ops + Memory `store_memory` (ADR-015); goals/workflows/executions/agents still shadow | Deepen remaining domains via ADR |
| Planner reads state | ✅ every `PLAN_REQUEST` resolves `StateContext` (payload or `SA.query`) | Keep; deepen |
| Goals / agents / workflows query WM | ✅ goals via `goal_lookup`; GoalEngine **RETIRED (ADR-012 A)**; workflows/agents execution-scoped | Soft duals documented; mutate deepen ADR-gated |
| Shadow SoT elimination | ✅ inventories closed (3a–6b + agents + ADR-014); Memory mutate **ADR-015** | Goals/workflows/executions/agents mutate — new ADRs |
| Domain types | ✅ `domain/state_authority.py` | Evolve without breaking bus dicts |

Existing types: `StateContext` (`domain/state_context.py`) is the v1 projection DTO (`StateProjection` alias). Evolve toward richer projections without breaking AppState reducers.

---

## Verification

| Gate | Command / artifact |
|------|-------------------|
| State chain probe | `python3 scripts/state_authority_verification_audit.py` |
| Truth matrix | `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md` |
| Bypass audit | Tom — no direct repo access from planner/UI |
| Workspace OS test | ADR-006 acceptance (no chat, full reconstruction) |

---

## Non-goals (blocked until contract v1 ships)

- OperatorKernel as authority (ADR-006)  
- New reasoning frameworks that bypass state query  
- Phase B UI expansion that masks missing state consumption  

---

## Next implementation steps (after Slice 1)

1. ~~Define `StateQuery`, `StateDelta`, `MutationReceipt` domain types (dataclasses).~~ ✅ Slice 1  
2. ~~Extend `StateAuthorityService` to implement full contract surface.~~ ✅ `query`/`project`; `mutate` stub  
3. ~~Route PlannerService to require state projection on every `PLAN_REQUEST`.~~ ✅ Slice 2  
4. ~~Inventory shadow SoT services; migration plan per domain (Goals dual-path first).~~ ✅ Slice 3 — `docs/architecture/SHADOW_SOT_INVENTORY.md`; GoalEngine quarantined from live factory  
5. ~~Add reconstruction acceptance test (no chat history).~~ ✅ thin probe (Slice 3) + journal recover with edges (Slice 4)  
6. ~~Unify `mutate()` onto World Model with real `MutationReceipt`s.~~ ✅ node ops (Slice 3) + edge ops (Slice 4); goals/workflows still deferred  

### Shadow SoT inventory (Slice 3–4)

| Domain | Status after Slice 4 |
|--------|----------------------|
| World Model nodes | ✅ authoritative via `SA.mutate` / `SA.query` |
| World Model edges | ✅ authoritative via `SA.mutate` (`create_edge` / `delete_edge`) |
| Goals (`GoalEngine` vs `GoalRepository`) | ✅ live = `GoalRepository`; GoalEngine **RETIRED (ADR-012 A)** |
| Workflows / executions / agents | ✅ 5a+5b / 6a+6b / ADR-013 inventories; keep outside SA mutate until new ADR |
| Memory | ✅ 4a–4d; **SA.mutate `store_memory` (ADR-015)**; tools soft dual to same SoT |
| Predictive / Undo packages | ✅ **RETIRED from live (ADR-014)** |

---

## References

- `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`  
- `docs/architecture/adr/ADR-005_WORLD_MODEL_AUTHORITY.md`  
- `docs/architecture/adr/ADR-012_GOALS_PHASE9_DISPOSITION.md`  
- `docs/architecture/adr/ADR-013_PLANNING_AGENT_COORDINATOR_DISPOSITION.md`  
- `docs/architecture/adr/ADR-014_PREDICTIVE_UNDO_DISPOSITION.md`  
- `docs/architecture/adr/ADR-015_STATE_AUTHORITY_MUTATE_MEMORY.md`  
- `docs/audits/R1_UNGATED_STOP_LINE.md`  
- `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md`  
- `docs/architecture/SHADOW_SOT_INVENTORY.md`  
- `ai_command_center/services/state_authority_service.py`  
- `ai_command_center/services/execution_authority_service.py` (`_project_state`)  
- `ai_command_center/core/service_factory.py`
