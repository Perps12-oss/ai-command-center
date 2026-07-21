# State Authority Contract

**Status:** ACTIVE (next architectural work after ADR-006)  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `ADR-005_WORLD_MODEL_AUTHORITY.md`, `ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`  
**Implementation today:** `ai_command_center/services/state_authority_service.py` (partial — projection only)  
**Milestone:** PHASE R1 Priority 3

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

State Authority **may aggregate** internally; callers must not care which store backs a projection:

| Domain | Current backing (evidence on `main`) | Authoritative? |
|--------|--------------------------------------|----------------|
| World Model | `WorldModel` + SQLite repo | ✅ primary (ADR-005) |
| Goals | `GoalRepository`, `GoalEngine` | ⚠️ parallel to scheduler |
| Memory | `MemoryGraphService` | ⚠️ lookup hook only |
| Timeline / executions | `ExecutionRunRepository`, events | ⚠️ partial |
| Workflows | `WorkflowRunRepository` | ⚠️ risk of shadow SoT |
| Agent runtime | `AgentRuntimeService` pipeline state | ⚠️ partial |
| UI | `AppState` | projection only — **never** authoritative |

**Objective:** one authoritative access layer — not “move everything into World Model overnight,” but **no durable truth outside the contract**.

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

| Capability | Today on `main` | Contract target |
|------------|-----------------|-----------------|
| `StateAuthorityService.project()` | ✅ wired into ExecutionAuthority | Keep; extend |
| `query()` with structured `StateQuery` | ❌ implicit via text tokens | Add |
| `mutate()` with `StateDelta` | ❌ scattered across services | Unify |
| Planner reads state | ⚠️ snippets when `planner_mode=state_aware` | Mandatory |
| Goals / agents / workflows query WM | ❌ per bypass audits | Wire through contract |
| Shadow SoT elimination | ❌ multiple repos | Registry + migration |

Existing types: `StateContext` (`domain/state_context.py`) is the v1 projection DTO. Evolve toward `StateQuery` / `StateProjection` / `StateDelta` / `MutationReceipt` without breaking AppState reducers.

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

## Next implementation steps (Devin, after Guardian approves contract v1 scope)

1. Define `StateQuery`, `StateDelta`, `MutationReceipt` domain types (dataclasses).  
2. Extend `StateAuthorityService` to implement full contract surface.  
3. Route PlannerService to require state projection on every `PLAN_REQUEST`.  
4. Inventory shadow SoT services; migration plan per domain.  
5. Add reconstruction acceptance test (no chat history).  

---

## References

- `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`  
- `docs/architecture/adr/ADR-005_WORLD_MODEL_AUTHORITY.md`  
- `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md`  
- `ai_command_center/services/state_authority_service.py`  
- `ai_command_center/services/execution_authority_service.py` (`_project_state`)
