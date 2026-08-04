# ADR-012: Goals Phase-9 (GoalEngine) Disposition

**Status:** Accepted — **Option A (retire)**  
**Date:** 2026-08-03 (Accepted 2026-08-04)  
**Deciders:** Product / architecture (human chose A)  
**Does not supersede:** ADR-006 (ExecutionAuthority remains sole intake)  
**Related:** `SHADOW_SOT_INVENTORY.md` step **3b**, `state_authority/GOALS_DUAL_PATH_INVENTORY.md`, `GOAL_ENGINE.md`, ADR-005, ADR-006  
**Baseline at proposal:** `e9d0c15` · **Accepted after:** #128 on `main`

---

## Continuity (this agent run)

| Item | Status |
|------|--------|
| Stage 2 Slice 4 PR [#127](https://github.com/Perps12-oss/ai-command-center/pull/127) | Closed (duplicate of #125 path) |
| ADR-012 Proposed | Merged #128 @ `328e942` |
| Edge mutate + Goals quarantine | On `main` via #125 / #126 |
| Dual-path inventory + `mutation_for_edge` DELETE | On `main` via #128 |
| **This acceptance** | Option **A** — Phase-9 retired from product path; schema/module cleanup optional later |

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

Phase-9 code and the `goal_engine_goals` schema **still exist in the tree** for unit tests until an optional cleanup PR. Step **3b** disposition is closed by this acceptance.

| | Live scheduler | Phase-9 GoalEngine |
|--|----------------|--------------------|
| Table | `goals` | `goal_engine_goals` |
| Domain | `domain.goal.Goal` | `orchestration.goals.goal.Goal` |
| Factory | Constructed + registered | **Retired from live path** (not constructed) |
| Intake | Sole `GOAL_SUBMIT_REQUEST` consumer | None — must not return |

Silent merge or dual-write is forbidden (ADR-006 + State Authority R1).

---

## Options (historical)

### Option A — Retire Phase-9 from the product tree — **CHOSEN**

Keep quarantine permanent. Optional later cleanup may archive or delete Phase-9 modules/schema.

**Acceptance checklist:**

1. ~~ADR status → Accepted (Option A)~~ ✅  
2. ~~Truth matrix: GoalEngine = **RETIRED**~~ ✅  
3. Optional follow-up: move under `research/` or delete with test updates — **separate**  
4. **No** factory flag to re-enable without a new ADR ✅  

### Option B — Merge into live scheduler — **NOT CHOSEN**

### Option C — Research opt-in flag — **NOT CHOSEN**

---

## Decision

**Accepted: Option A — Retire Phase-9 GoalEngine from the product / live path.**

Binding rules:

- Do **not** construct or register `GoalEngine` in `service_factory` / application composition  
- Do **not** subscribe GoalEngine to `GOAL_SUBMIT_REQUEST` or any intake topic  
- Do **not** implement `SA.mutate` for goals via Phase-9 stores  
- Re-introduction as live authority requires a **new ADR** that supersedes this decision  
- Deleting `goal_engine_goals` / relocating Phase-9 packages is **allowed** in a follow-up cleanup PR; not required for acceptance  

Live goals SoT remains:

```text
GoalRepository + SingleGoalScheduler (+ SA.goal_lookup reads)
```

---

## Consequences (in force)

| Area | Effect |
|------|--------|
| `SHADOW_SOT_INVENTORY` 3b | ✅ **closed** (Option A) |
| SA `goal_lookup` | Unchanged (`GoalRepository`) |
| `SA.mutate` goals | Later slice only |
| Memory / Workflows inventory | **Unblocked** (SHADOW steps 4–5) |
| Phase-9 tree | May remain for unit tests until cleanup PR |

---

## Out of scope (this acceptance PR)

- Schema deletion or package relocation  
- OperatorKernel, Goose, Async EventBus  
- Memory / workflow SA routing implementation (next Stage 2 work)  

---

## Verification

| Check | How |
|-------|-----|
| Decision recorded | Status = Accepted — Option A |
| No dual intake | `GOAL_SUBMIT_REQUEST` → scheduler only |
| Factory | GoalEngine absent from `build_services` |
| Matrix | GoalEngine = **RETIRED** |
| Re-wire guard | New ADR required to supersede |

---

## References

- `docs/architecture/SHADOW_SOT_INVENTORY.md`  
- `docs/architecture/state_authority/GOALS_DUAL_PATH_INVENTORY.md`  
- `docs/architecture/GOAL_ENGINE.md`  
- `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`  
- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`  
- `ai_command_center/core/service_factory.py`  
- `ai_command_center/orchestration/goals/goal_engine.py`  
