# Goals Dual-Path Shadow SoT Inventory

**Status:** CLOSED for 3b — Path A sole product SoT; Path B **RETIRED** (ADR-012 A)  
**Authority:** `STATE_AUTHORITY_CONTRACT.md`, ADR-006, R1.3, **ADR-012 Accepted Option A**  
**Date:** 2026-07-30 (updated 2026-08-04)  
**Baseline:** `origin/main` @ `328e942`+  
**3b decision:** ADR-012 **Accepted — Option A (retire)**; schema/module cleanup optional later

## Verdict

Goals had **two parallel persistence stacks**. Only Path A is live. Path B
(`GoalEngine`) is **retired from the product path** (ADR-012 A). State Authority
reads Path A only. **Do not re-wire GoalEngine into intake without a new ADR
that supersedes ADR-012.**

| Path | Stack | Live intake? | SA `goal_lookup`? | Disposition |
|------|-------|:------------:|:-----------------:|-------------|
| **A — Scheduler (canonical)** | `ExecutionAuthority` → `GOAL_SUBMIT_REQUEST` → `SingleGoalScheduler` → `GoalRepository` (`goals` table) | ✅ | ✅ | **keep** — sole live SoT for UI goals |
| **B — GoalEngine (retired)** | `GoalEngine` + `SQLiteGoalEngineRepository` (`goal_engine_goals` table) | ❌ | ❌ | **RETIRED (ADR-012 A)** — not constructed; unit-test tree only until cleanup |

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
| 3 | ✅ **ADR-012 Accepted — Option A (retire)** | Human 2026-08-04 |
| 4 | Optional cleanup: archive/delete Phase-9 modules + `goal_engine_goals` | Separate PR |
| 5 | Optional: `SA.mutate` goal ops only via live SoT | Contract R1 |

**Hard rule (ADR-012 A):** no factory construction of GoalEngine onto intake; re-wire requires a new ADR. Schema drop is optional cleanup, not required for acceptance.

## Related shadow SoT

| Domain | Status after Slice 4 |
|--------|----------------------|
| WM nodes | ✅ via `SA.mutate` / `SA.query` |
| WM edges | ✅ via `SA.mutate` create_edge / delete_edge |
| Goals | ✅ live Path A; Path B quarantined |
| Workflows / executions / agents | ⚠️ outside SA mutate |
| Memory | ⚠️ lookup on query only |

## References

- `docs/architecture/adr/ADR-012_GOALS_PHASE9_DISPOSITION.md`
- `docs/architecture/SHADOW_SOT_INVENTORY.md`
- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`
- `docs/architecture/GOAL_ENGINE.md`
- `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`
- `ai_command_center/core/service_factory.py`
- `ai_command_center/services/goal_scheduler_service.py`
- `ai_command_center/orchestration/goals/goal_engine.py`
