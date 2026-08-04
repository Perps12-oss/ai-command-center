# ADR-012: Goals Phase-9 (GoalEngine) Disposition

**Status:** Proposed (awaiting human decision)  
**Date:** 2026-08-03  
**Deciders:** Product / architecture (pending)  
**Does not supersede:** ADR-006 (ExecutionAuthority remains sole intake)  
**Related:** `SHADOW_SOT_INVENTORY.md` step **3b**, `state_authority/GOALS_DUAL_PATH_INVENTORY.md`, `GOAL_ENGINE.md`, ADR-005, ADR-006  
**Baseline:** `origin/main` @ `e9d0c15` (#125 quarantine)

---

## Continuity (this agent run)

| Item | Status |
|------|--------|
| Stage 2 Slice 4 PR [#127](https://github.com/Perps12-oss/ai-command-center/pull/127) | Parallel overlap with #125; **close as duplicate** (agent lacked close token — please close manually) |
| Edge mutate + Goals quarantine | Already on `main` via #125 / #126 — **not** re-implemented here |
| Salvaged from #127 into this proposal | Dual-path inventory detail; optional small `mutation_for_edge` DELETE helper (WM only, not goals schema) |
| This ADR | **Proposal only** — no `goal_engine_goals` drop, no intake rewire |

---

## Context

Stage 2 Slice 3 quarantined Phase-9 `GoalEngine` + `SQLiteGoalEngineRepository` from the live composition root (`service_factory.py`). Live goals are:

```text
UI / ExecutionAuthority
  → GOAL_SUBMIT_REQUEST
  → SingleGoalScheduler
  → GoalRepository (table: goals)
  → AppState / SA.goal_lookup
```

Phase-9 code and the `goal_engine_goals` schema **still exist in the tree** for unit tests and research. Step **3b** in `SHADOW_SOT_INVENTORY.md` requires an explicit disposition before further Goals work (including any future `SA.mutate` for goals).

Two durable models remain conceptually divergent:

| | Live scheduler | Phase-9 GoalEngine |
|--|----------------|--------------------|
| Table | `goals` | `goal_engine_goals` |
| Domain | `domain.goal.Goal` | `orchestration.goals.goal.Goal` |
| Status enum | scheduler `GoalStatus` | Phase-9 `goal_status.GoalStatus` |
| Factory | Constructed + registered | **Quarantined** (not constructed) |
| Intake | Sole `GOAL_SUBMIT_REQUEST` consumer | None |

Silent merge or dual-write is forbidden (ADR-006 + State Authority R1).

---

## Options

### Option A — Retire Phase-9 from the product tree

**Meaning:** Keep quarantine permanent. Mark GoalEngine / `goal_engine_goals` as research-archived or remove in a later cleanup PR after acceptance of this ADR.

| Pros | Cons |
|------|------|
| One goals SoT forever | Loses richer Phase-9 fields (tags, parent_goal_id, deadline, …) unless re-specified on scheduler model |
| Lowest runtime risk | Docs (`GOAL_ENGINE.md`) become historical |
| Matches ADR-006 “don’t rewire alternate engines” | Migration of any leftover DB rows is discard/export-only |

**Acceptance if chosen:**

1. ADR status → Accepted (Option A)  
2. Truth matrix: GoalEngine = **RETIRED** (or archived path)  
3. Optional follow-up PR: move Phase-9 modules under `research/` or delete with test updates — **separate** from acceptance  
4. **No** factory flag to re-enable without a new ADR  

### Option B — Merge Phase-9 model into the live scheduler SoT

**Meaning:** Evolve `GoalRepository` / `domain.goal` toward the Phase-9 contract (or a negotiated subset), one-time migrate `goal_engine_goals` → `goals`, then retire the Phase-9 engine class.

| Pros | Cons |
|------|------|
| Keeps richer goal semantics | Schema + domain migration; high test surface |
| Aligns `GOAL_ENGINE.md` intent with live path | Easy to accidentally dual-write during transition |
| SA goal projections can grow fields intentionally | Requires explicit field mapping + rollback plan |

**Acceptance if chosen:**

1. ADR status → Accepted (Option B) with field map appendix  
2. Migration script + tests (empty DB + sample rows)  
3. Factory remains single SoT — GoalEngine class still not on intake  
4. Only after migrate green: drop or freeze `goal_engine_goals`  

### Option C — Explicit research opt-in (not recommended as end state)

Factory flag `ACC_ENABLE_GOAL_ENGINE=1` constructs GoalEngine for experiments only, still **not** on `GOAL_SUBMIT_REQUEST`. Delays SoT clarity; only acceptable as a time-boxed research exemption with an expiry note in this ADR.

---

## Decision

**PENDING HUMAN CHOICE — A, B, or time-boxed C.**

Until Accepted:

- Do **not** delete `goal_engine_goals` or Phase-9 modules  
- Do **not** register GoalEngine on intake topics  
- Do **not** implement `SA.mutate` for goals  
- Quarantine (Slice 3a) remains in force  

---

## Recommendation (non-binding)

**Prefer Option A (retire)** unless product explicitly needs Phase-9 fields on the live path in the near term. Rationale: live scheduler already owns intake (ADR-006); quarantine is proven; merge cost is high relative to Stage 2’s next soft-shadow work (Memory → SA, Workflows).

If richer goals are required soon, choose **B** with a written field map before any code migration.

---

## Consequences (after acceptance)

| Area | A — Retire | B — Merge |
|------|------------|-----------|
| `SHADOW_SOT_INVENTORY` 3b | ✅ closed | ✅ closed after migrate |
| SA `goal_lookup` | Unchanged (GoalRepository) | May expose new fields |
| `SA.mutate` goals | Still a later slice | Still after single SoT |
| Memory / Workflows inventory | Unblocked to proceed in parallel once 3b decided | Same |

---

## Out of scope (this proposal)

- Schema deletion or data migration  
- OperatorKernel, Goose, Async EventBus  
- Mission Control UX  
- Memory / workflow SA routing (steps 4–5) — next after 3b decision  

---

## Verification (when Accepted)

| Check | How |
|-------|-----|
| Decision recorded | This ADR Status = Accepted + chosen option |
| No dual intake | `GOAL_SUBMIT_REQUEST` subscribers = scheduler only |
| Factory | GoalEngine still absent unless Option C flag documented |
| Matrix | GoalEngine row matches chosen disposition |
| If B | Migration tests green; no dual-write period without feature flag |

---

## References

- `docs/architecture/SHADOW_SOT_INVENTORY.md`  
- `docs/architecture/state_authority/GOALS_DUAL_PATH_INVENTORY.md`  
- `docs/architecture/GOAL_ENGINE.md`  
- `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`  
- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`  
- `ai_command_center/core/service_factory.py`  
- `ai_command_center/orchestration/goals/goal_engine.py`  
- `ai_command_center/repositories/goal_repository.py`  
- `ai_command_center/repositories/goal_engine_repository.py`  
