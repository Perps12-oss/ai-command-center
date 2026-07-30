# State Authority Contract

**Status:** ACTIVE (next architectural work after ADR-006)  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `ADR-005_WORLD_MODEL_AUTHORITY.md`, `ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`  
**Implementation today:** `ai_command_center/services/state_authority_service.py`  
**Domain types:** `ai_command_center/domain/state_authority.py` (`StateQuery`, `StateProjection`, `StateDelta`, `MutationReceipt`, `ProjectionScope`)  
**Milestone:** PHASE R1 Priority 3 / Stage 2 (Slices 1–4: query, planner mandate, WM node+edge mutate, Goals dual-path inventory)

---

## Purpose

ACC has a **canonical execution path** (ADR-006). The next maturity gap is **authoritative state access**:

```text
Execution ownership  → mostly solved (ExecutionAuthority chain)
State ownership      → not solved (many parallel stores, weak consumption)
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
| World Model | `WorldModel` + SQLite repo | ✅ primary (ADR-005) | Aggregate via `query` / `project`; mutate nodes **and** edges |
| Goals | `GoalRepository` (SA lookup) **and** `GoalEngine` (constructed-only shadow) | ⚠️ dual path | Inventory published — see `state_authority/GOALS_DUAL_PATH_INVENTORY.md`; SA uses `goal_repo` only |
| Memory | `MemoryGraphService` | ⚠️ lookup hook only | Aggregate via optional `memory_lookup` |
| Timeline / executions | `ExecutionRunRepository`, events | ⚠️ partial | Out of Slice 4 mutate |
| Workflows | `WorkflowRunRepository` | ⚠️ risk of shadow SoT | Inventory; no silent merge |
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
| `world_model.mutation.applied` | Published by SA after successful `mutate()` node/edge ops |

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

| Capability | Today on `main` (post Slice 4) | Contract target |
|------------|--------------------------------|-----------------|
| `StateAuthorityService.project()` | ✅ wired into ExecutionAuthority; delegates to `query` | Keep; extend |
| `query()` with structured `StateQuery` | ✅ Stage 2 Slice 1 | Keep; deepen filters |
| `mutate()` with `StateDelta` | ✅ WM node + edge create/delete + receipt (Slice 4) | Deepen; unify remaining domains |
| Planner reads state | ✅ every `PLAN_REQUEST` resolves `StateContext` | Keep; deepen |
| Goals / agents / workflows query WM | ⚠️ goals via lookup; dual GoalEngine inventory | Wire through contract after migrate |
| Shadow SoT elimination | ⚠️ Goals inventoried; workflows/agents remain | Registry + migration |
| Domain types | ✅ `domain/state_authority.py` | Evolve without breaking bus dicts |

Existing types: `StateContext` (`domain/state_context.py`) is the v1 projection DTO (`StateProjection` alias). Evolve toward richer projections without breaking AppState reducers.

---

## Verification

| Gate | Command / artifact |
|------|-------------------|
| State chain probe | `python3 scripts/state_authority_verification_audit.py` |
| Truth matrix | `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md` |
| Goals dual-path inventory | `docs/architecture/state_authority/GOALS_DUAL_PATH_INVENTORY.md` |
| Bypass audit | Tom — no direct repo access from planner/UI |
| Workspace OS test | ADR-006 acceptance (no chat, full reconstruction) |

---

## Non-goals (blocked until contract v1 ships)

- OperatorKernel as authority (ADR-006)  
- New reasoning frameworks that bypass state query  
- Phase B UI expansion that masks missing state consumption  

---

## Next implementation steps

1. ~~Define `StateQuery`, `StateDelta`, `MutationReceipt` domain types (dataclasses).~~ ✅ Slice 1  
2. ~~Extend `StateAuthorityService` to implement full contract surface.~~ ✅ `query`/`project`; `mutate` nodes+edges  
3. ~~Route PlannerService to require state projection on every `PLAN_REQUEST`.~~ ✅ Slice 2  
4. ~~Inventory shadow SoT services; migration plan per domain (Goals dual-path first).~~ ✅ Slice 4 inventory  
5. ~~Add reconstruction acceptance test (no chat history).~~ ✅ thin mutate→query probe (Slice 3)  
6. ~~Unify `mutate()` onto World Model with real `MutationReceipt`s.~~ ✅ nodes (Slice 3) + edges (Slice 4)  
7. Execute Goals migration plan (retire GoalEngine or ADR converge) — **not** silent intake merge  
8. Inventory workflows / agents / memory mutate paths  

### Shadow SoT inventory (Slice 4)

| Domain | Status after Slice 4 |
|--------|----------------------|
| World Model nodes | ✅ authoritative via `SA.mutate` / `SA.query` |
| World Model edges | ✅ authoritative via `SA.mutate` create_edge / delete_edge |
| Goals (`GoalEngine` vs `GoalRepository`) | ⚠️ dual path — inventory + migration plan published |
| Workflows / executions / agents | ⚠️ outside SA mutate |
| Memory | ⚠️ lookup hook on query; not mutate |

---

## References

- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`  
- `docs/architecture/state_authority/GOALS_DUAL_PATH_INVENTORY.md`  
- `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`  
- `docs/architecture/adr/ADR-005_WORLD_MODEL_AUTHORITY.md`  
- `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md`  
- `ai_command_center/services/state_authority_service.py`  
- `ai_command_center/services/execution_authority_service.py` (`_project_state`)
