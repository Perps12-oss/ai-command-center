# Goals Dual-Path Shadow SoT Inventory

**Status:** ACTIVE inventory (Stage 2 Slice 4) — complements `SHADOW_SOT_INVENTORY.md`  
**Authority:** `STATE_AUTHORITY_CONTRACT.md`, ADR-006, R1.3  
**Date:** 2026-07-30  
**Baseline:** `origin/main` @ `e9d0c15` (#125 quarantine + edge mutate)

## Verdict

Goals had **two parallel persistence stacks**. Only Path A is live. Path B
(`GoalEngine`) is **quarantined from the composition root** (Slice 3 / #125).
State Authority reads Path A only. **Do not re-wire GoalEngine into intake
without an ADR.**

| Path | Stack | Live intake? | SA `goal_lookup`? | Disposition |
|------|-------|:------------:|:-----------------:|-------------|
| **A — Scheduler (canonical)** | `ExecutionAuthority` → `GOAL_SUBMIT_REQUEST` → `SingleGoalScheduler` → `GoalRepository` (`goals` table) | ✅ | ✅ | **keep** — sole live SoT for UI goals |
| **B — GoalEngine (shadow)** | `GoalEngine` + `SQLiteGoalEngineRepository` (`goal_engine_goals` table) | ❌ | ❌ | **QUARANTINED** — not constructed in factory; research/tests only |

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

## Path B — Quarantined (exists in tree, not constructed)

```text
service_factory (Slice 3+):
  # GoalEngine intentionally omitted — SHADOW_SOT_INVENTORY.md
  → NOT constructed
  → NOT on WiredServices
  → NOT subscribed to GOAL_SUBMIT_REQUEST
  → schema code remains under repositories/goal_engine_repository.py for tests
```

Evidence:

| Probe | Location |
|-------|----------|
| Quarantine | `service_factory.py` comments + omitted construct |
| Schema | `goal_engine_repository.py` → `goal_engine_goals` |
| Domain | `orchestration/goals/goal_engine.py` (Phase-9 richer model) |
| Contract doc | `docs/architecture/GOAL_ENGINE.md` — **Proposed**, pending approval |
| Inventory | `docs/architecture/SHADOW_SOT_INVENTORY.md` |

Exists ≠ Wired ≠ Authoritative. Path B is **tree-only / unit-testable**.

## Divergence risks (mitigated)

1. **Dual tables** — `goals` vs `goal_engine_goals` never sync; quarantine stops bootstrap dual-create.
2. **Truth matrix** — GoalEngine marked **QUARANTINED** (not live WIRED).
3. **SA blind spot** — if callers write Path B in tests/research, `SA.query(include_goals=True)` will not see those goals.
4. **ADR-006** — OperatorKernel / alternate engines must not become intake; GoalEngine must not be quietly wired to `GOAL_SUBMIT_REQUEST`.

## Migration plan (ordered)

| Step | Action | Gate |
|------|--------|------|
| 1 | ✅ Inventory published | Doc honesty |
| 2 | ✅ Quarantine GoalEngine from live factory (#125) | R1.3 |
| 3 | Decide: **retire** Path B schema **or** ADR to converge with scheduler | Human + ADR |
| 4 | If converge: single repository + one-time migration; never dual-write | Migration tests |
| 5 | Optional: `SA.mutate` goal ops only after single SoT exists | Contract R1 |

**Hard rule until step 3 ADR:** no factory construction of GoalEngine onto intake topics; no SA mutate for goals.

## Related shadow SoT

| Domain | Status after Slice 4 |
|--------|----------------------|
| WM nodes | ✅ via `SA.mutate` / `SA.query` |
| WM edges | ✅ via `SA.mutate` create_edge / delete_edge |
| Goals | ✅ live Path A; Path B quarantined |
| Workflows / executions / agents | ⚠️ outside SA mutate |
| Memory | ⚠️ lookup on query only |

## References

- `docs/architecture/SHADOW_SOT_INVENTORY.md`
- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`
- `docs/architecture/GOAL_ENGINE.md`
- `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`
- `ai_command_center/core/service_factory.py`
- `ai_command_center/services/goal_scheduler_service.py`
- `ai_command_center/orchestration/goals/goal_engine.py`
