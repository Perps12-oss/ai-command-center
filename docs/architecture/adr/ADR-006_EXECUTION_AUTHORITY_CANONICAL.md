# ADR-006: ExecutionAuthority as Canonical Runtime Authority

**Status:** Accepted  
**Date:** 2026-07-21  
**Deciders:** Product / architecture (Answer A)  
**Supersedes:** Any plan treating OperatorKernel as live intake authority  
**Related:** `ADR-005_WORLD_MODEL_AUTHORITY.md`, `docs/architecture/STATE_AUTHORITY_CONTRACT.md`, `docs/audits/RUNTIME_AUTHORITY_MAP.md`

---

## Context

Runtime audits on `origin/main` identified two competing authority stories:

1. **Live path** — `ExecutionAuthorityService` owns `UI_COMMAND` intake, projects state via `StateAuthorityService`, dispatches through goal scheduling, planning, and orchestration.
2. **Paper path** — `OperatorKernel` → `PlanningEngine` → `AgentCoordinator` exists as library + tests only; not registered in `service_factory.py` or the composition root.

Choosing the paper path would require replacing live intake, rewiring the composition root, and re-validating the entire execution chain — without addressing the audits' primary finding: **state authority is immature**, not execution intake.

---

## Decision

**`ExecutionAuthorityService` is the canonical runtime intake and execution authority path.**

The verified live chain on `origin/main`:

```text
UI_COMMAND
  → ExecutionAuthorityService (+ StateAuthorityService.project)
  → GOAL_SUBMIT_REQUEST
  → SingleGoalScheduler
  → PlannerService (PLAN_REQUEST) OR synthetic plan
  → EXECUTION_RUN_REQUEST
  → ExecutionOrchestratorService
  → ChatHandler / CapabilityRuntime / Tools
  → OrchestrationService (receipts / truth)
  → AppState → UI
```

**`OperatorKernel` is non-canonical** — research / future-state components only.

Promotion of OperatorKernel requires **all** of:

1. Integration into `service_factory` with explicit ownership  
2. Runtime execution ownership audit (no dual intake)  
3. Demonstrated superiority over the ExecutionAuthority path for a defined request class  
4. A new ADR explicitly superseding this decision  

Until then: **ExecutionAuthority is the sole authority path for user intake and execution dispatch.**

---

## Rationale

| Factor | ExecutionAuthority (A) | OperatorKernel migration (B) |
|--------|------------------------|------------------------------|
| Live on `main` | ✅ wired in factory | ❌ tests only |
| Composition root | ✅ | ❌ |
| User intake | ✅ `UI_COMMAND` | ❌ |
| Audit evidence | ✅ `RUNTIME_AUTHORITY_MAP.md` | ❌ paper path |
| Migration cost | Evolution (State Authority) | Full authority replacement |

Replacing ExecutionAuthority does not automatically fix state consumption gaps. The audits indicate **execution ownership is mostly solved; authoritative state access is not.**

---

## Consequences

### Stop (until State Authority contract is implemented)

- OperatorKernel integration as runtime authority  
- Advanced reasoning-loop experiments that bypass ExecutionAuthority intake  
- ReAct / agent-framework experiments that create shadow execution paths  
- Debating intake ownership — **closed by this ADR**

### Continue (Priority order — see `PHASE_R1_RUNTIME_RECONCILIATION.md`)

1. ~~Runtime authority decision~~ ✅ this ADR  
2. Composition root registry (no orphan subsystems)  
3. **State Authority contract** — `STATE_AUTHORITY_CONTRACT.md`  
4. UI primitive convergence (after state path)  
5. Feature completion (predictive, undo, platform) — after state + authority aligned  

### OperatorKernel allowed uses

- Unit / golden tests  
- Internal libraries consumed **through** ExecutionAuthority or Planner (if promoted later via ADR)  
- Research spikes on branches — not merged as parallel intake  

### Demoted components (supporting, not intake)

| Component | Role |
|-----------|------|
| `CommandRouterService` | Workspace tracker + classify facade |
| `RuntimeCapabilityRouterService` | Capability kind / provider map |
| `ChatHandlerService` | LLM PlanStep handler |
| `OrchestrationService` | Completion observer / receipts |

---

## Success criteria

1. All user execution intake flows through `ExecutionAuthorityService`.  
2. All execution decisions are derived from **State Authority projections** (evolving — see contract).  
3. All execution outcomes mutate authoritative state through defined mutation paths.  
4. All UI surfaces project `AppState` — never shadow SoT.  
5. **No subsystem may maintain authoritative state outside State Authority** (strengthens ADR-005; see `STATE_AUTHORITY_CONTRACT.md`).

### Acceptance test (Workspace OS bar)

Delete every conversation. Restart ACC.

ACC must still answer from persistent state (not chat history):

- What goals are active?  
- What notes exist?  
- What workflows are running?  
- What relationships exist?  
- What happened this week (timeline / journal)?  

Passing this test means identity depends on **persistent state**, not conversation context.

---

## Verification

- `docs/audits/RUNTIME_AUTHORITY_MAP.md` — live vs paper paths  
- `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md` — composition registry  
- `scripts/state_authority_verification_audit.py` — state chain probes  
- Tom / Guardian audits reject PRs that introduce dual intake or OperatorKernel factory wiring without superseding ADR  

---

## 12. Gate addendum — B5 Fork 1 (Hero intake)

**Date:** 2026-08-16  
**Owner decision:** Fork 1 (closed on `main` by [#168](https://github.com/Perps12-oss/ai-command-center/pull/168), 2026-08-12).  
**Does not supersede** this ADR. Records a boundary that was implied by “sole user intake” and is now explicit.

### Decision

`GOAL_SUBMIT_REQUEST` is an **internal post-authority** command. It is not a UI intake topic.

1. User-facing “New Goal” (Command Center / Goal Dashboard Hero Immediate Action) publishes **`UI_COMMAND`** with a `goal:` prefix (plus optional priority, description, workspace scope).
2. `ExecutionAuthorityService` remains the only production publisher of `GOAL_SUBMIT_REQUEST`, and only after `analyze` / `_publish_decision` / `_admit` (State Authority projection).
3. `SingleGoalScheduler` **refuses** submits that lack a non-empty `authority_decision` dict. Direct UI (or any non-EA) publish cannot admit a goal.
4. Goal lifecycle facts (`GOAL_ACTIVATED`, `GOAL_PAUSED`, `GOAL_CANCELLED`) remain service-owned. UI must not publish them.

Forbidden:

```text
Hero Immediate Action → GOAL_SUBMIT_REQUEST → SingleGoalScheduler
```

Required:

```text
Hero Immediate Action
  → UI_COMMAND (goal: <title>)
  → ExecutionAuthorityService
  → GOAL_SUBMIT_REQUEST (authority_decision stamped, source=execution_authority)
  → SingleGoalScheduler
```

### What this does not change

- OperatorKernel remains non-canonical (body of this ADR).
- SA mutate (ADR-016) does not use `GOAL_SUBMIT_REQUEST`.
- Broader publisher refactors beyond Hero New Goal are out of scope.

### Verification

- `tests/test_b5_hero_ea_intake.py`
- `scripts/verify_ui_constitution.py` — UIController must not reference `GOAL_SUBMIT_REQUEST`
- `docs/UI_CONSTITUTION.md` Articles 7, 8, 16
- `docs/audits/B5_HERO_EA_INTAKE_CHANGE_NOTE.md`

---

## Revision history

| Date | Change |
|------|--------|
| 2026-07-21 | Accepted — Answer A (ExecutionAuthority canonical) |
| 2026-08-16 | §12 — B5 Fork 1: Hero New Goal via `UI_COMMAND`; `GOAL_SUBMIT_REQUEST` is EA-only post-authority |
