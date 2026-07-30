# Goals Dual-Path Shadow SoT Inventory

**Status:** ACTIVE inventory (Stage 2 Slice 4)  
**Authority:** `STATE_AUTHORITY_CONTRACT.md`, ADR-006, R1.3  
**Date:** 2026-07-30  
**Baseline:** `origin/main` @ `77b4baa`

## Verdict

Goals have **two parallel persistence stacks**. Only one is on the live intake path.
State Authority reads the live path only. **Do not merge GoalEngine into intake
in this slice.**

| Path | Stack | Live intake? | SA `goal_lookup`? | Disposition |
|------|-------|:------------:|:-----------------:|-------------|
| **A — Scheduler (canonical)** | `ExecutionAuthority` → `GOAL_SUBMIT_REQUEST` → `SingleGoalScheduler` → `GoalRepository` (`goals` table) | ✅ | ✅ | **keep** — sole live SoT for UI goals |
| **B — GoalEngine (shadow)** | `GoalEngine` + `SQLiteGoalEngineRepository` (`goal_engine_goals` table) | ❌ | ❌ | **retire or research-only** — constructed in factory, not registered, not on intake |

## Path A — Live (authoritative for UI / intake)

```text
UI / ExecutionAuthority
      → GOAL_SUBMIT_REQUEST
      → SingleGoalScheduler
      → GoalRepository (table: goals)
      → GOAL_SUBMITTED / lifecycle topics
      → AppState reducers + GlobalContextBar
```

Evidence:

| Probe | Location |
|-------|----------|
| Intake emit | `execution_authority_service.py` publishes `GOAL_SUBMIT_REQUEST` |
| UI emit | `ui/controller.py`, Hero New Goal → same topic |
| Consumer | `goal_scheduler_service.py` subscribes `GOAL_SUBMIT_REQUEST` |
| Persistence | `repositories/goal_repository.py` → `goals` |
| SA aggregation | `service_factory._goal_lookup` → `goal_repo.list_goals()` only |
| Registered | `goal_scheduler` in `services.register(...)` loop |

## Path B — Shadow (exists, not intake)

```text
service_factory constructs:
  GoalEngine(bus, SQLiteGoalEngineRepository(db))
  → returned on WiredServices.goal_engine
  → NOT in services.register(...)
  → does NOT subscribe to GOAL_SUBMIT_REQUEST
  → persists to goal_engine_goals (separate schema)
```

Evidence:

| Probe | Location |
|-------|----------|
| Construct | `service_factory.py` ~L200 |
| Hold | `WiredServices.goal_engine` |
| Schema | `goal_engine_repository.py` → `goal_engine_goals` |
| Domain | `orchestration/goals/goal_engine.py` (Phase-9 richer model) |
| Contract doc | `docs/architecture/GOAL_ENGINE.md` — **Proposed**, pending approval |

Exists ≠ Wired ≠ Authoritative. Path B is **constructed-only**.

## Divergence risks

1. **Dual tables** — `goals` vs `goal_engine_goals` never sync; silent dual-write would create split brain.
2. **Truth matrix drift** — earlier rows marked GoalEngine “WIRED / live” incorrectly; corrected in Slice 4 matrix update.
3. **SA blind spot** — if callers write Path B, `SA.query(include_goals=True)` will not see those goals.
4. **ADR-006** — OperatorKernel / alternate engines must not become intake; GoalEngine must not be quietly wired to `GOAL_SUBMIT_REQUEST`.

## Migration plan (ordered; later slices)

| Step | Action | Gate |
|------|--------|------|
| 1 | ✅ **This slice** — publish inventory; keep SA on Path A only | Doc + matrix honesty |
| 2 | Mark GoalEngine **research-only** in composition registry (same class as OperatorKernel disposition) | R1.2 / R1.3 |
| 3 | Decide: **retire** Path B (delete or quarantine under research/) **or** explicit ADR to supersede scheduler with GoalEngine | Human + ADR |
| 4 | If converge: single repository contract + one-time migration from `goal_engine_goals` → `goals` (or reverse); never dual-write | Migration tests |
| 5 | Optional: `SA.mutate` goal ops only after single SoT exists | Contract R1 |

**Hard rule until step 3 ADR:** no factory registration of GoalEngine onto intake topics; no SA mutate for goals.

## Related shadow SoT (not this inventory)

| Domain | Status after Slice 4 |
|--------|----------------------|
| WM nodes | ✅ via `SA.mutate` / `SA.query` |
| WM edges | ✅ via `SA.mutate` create_edge / delete_edge |
| Goals | ⚠️ dual path — this document |
| Workflows / executions / agents | ⚠️ outside SA mutate |
| Memory | ⚠️ lookup on query only |

## References

- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`
- `docs/architecture/GOAL_ENGINE.md`
- `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`
- `ai_command_center/core/service_factory.py`
- `ai_command_center/services/goal_scheduler_service.py`
- `ai_command_center/orchestration/goals/goal_engine.py`
