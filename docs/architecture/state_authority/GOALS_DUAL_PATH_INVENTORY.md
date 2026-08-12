# Goals Dual-Path Shadow SoT Inventory

**Status:** CLOSED for 3b (ADR-012 A) + **step 5 mutate submit** (ADR-016)  
**Authority:** `STATE_AUTHORITY_CONTRACT.md`, ADR-006, R1.3, **ADR-012 A**, **ADR-016**  
**Date:** 2026-07-30 (updated 2026-08-04)  
**Baseline:** ADR-016 acceptance tip  
**3b decision:** ADR-012 **Accepted — Option A (retire)**; schema/module cleanup optional later  
**5 decision:** ADR-016 **Accepted** — `SA.mutate(submit_goal)` via scheduler only

## Verdict

Goals had **two parallel persistence stacks**. Only Path A is live. Path B
(`GoalEngine`) is **retired from the product path** (ADR-012 A). State Authority
reads Path A and may **submit** via Path A′ (ADR-016). **Do not re-wire GoalEngine
into intake without a new ADR that supersedes ADR-012.** **Do not** let SA write
`GoalRepository` directly.

| Path | Stack | Live intake? | SA? | Disposition |
|------|-------|:------------:|:---:|-------------|
| **A — Scheduler (canonical)** | `GOAL_SUBMIT_REQUEST` → `SingleGoalScheduler` → `GoalRepository` (`goals`) | ✅ | ✅ lookup | **keep** — sole live SoT |
| **A′ — SA mutate (ADR-016)** | `SA.mutate(submit_goal)` → `submit_goal_for_state` → `submit_goal` | ✅ soft dual entry | ✅ mutate | **5 ✅** — same SoT as A |
| **B — GoalEngine (retired)** | `GoalEngine` + `goal_engine_goals` | ❌ | ❌ | **RETIRED (ADR-012 A)** |

## Path A — Live (authoritative for UI / intake)

```text
UI → UI_COMMAND (Hero: goal: <title>) → ExecutionAuthority
      → EXECUTION_AUTHORITY_DECISION + admit
      → GOAL_SUBMIT_REQUEST (authority_decision stamped)
      → SingleGoalScheduler
      → GoalRepository (table: goals)
      → GOAL_SUBMITTED / lifecycle topics
      → AppState reducers + GlobalContextBar
```

Evidence:

| Probe | Location |
|-------|----------|
| Intake emit | `execution_authority_service.py` publishes `GOAL_SUBMIT_REQUEST` |
| UI emit | `ui/controller.py` Hero New Goal → `UI_COMMAND` only (B5 fork 1; no direct scheduler topic) |
| Consumer | `goal_scheduler_service.py` subscribes `GOAL_SUBMIT_REQUEST` (refuses without `authority_decision`) |
| Persistence | `repositories/goal_repository.py` → `goals` |
| SA aggregation | `service_factory._goal_lookup` → `goal_repo.list_goals()` only |
| Registered | `goal_scheduler` in `services.register(...)` loop |

## Path A′ — SA mutate (ADR-016)

```text
Caller
  → StateAuthorityService.mutate(StateDelta(operations=[{op: submit_goal, title, …}]))
  → goal_submit → SingleGoalScheduler.submit_goal_for_state
  → submit_goal → goals + GOAL_SUBMITTED (+ maybe activate / PLAN_REQUEST)
  → MutationReceipt.applied[]   # never WorldModel.apply / GoalRepository from SA
```

Hard rules:

- No SA → `GoalRepository` direct writes  
- No GoalEngine path  
- Lifecycle (pause/resume/cancel) stays on scheduler request topics — **not** SA  

## Path B — Quarantined (exists in tree, not constructed)

```text
service_factory (Slice 3+):
  # GoalEngine intentionally omitted — SHADOW_SOT_INVENTORY.md
  → NOT constructed
  → NOT on WiredServices
  → NOT subscribed to GOAL_SUBMIT_REQUEST
  → schema code remains under repositories/goal_engine_repository.py for tests
```

Exists ≠ Wired ≠ Authoritative. Path B is **tree-only / unit-testable**.

## Divergence risks (mitigated)

1. **Dual tables** — `goals` vs `goal_engine_goals` never sync; quarantine stops bootstrap dual-create.
2. **Truth matrix** — GoalEngine marked **QUARANTINED** (not live WIRED).
3. **SA blind spot** — if callers write Path B in tests/research, `SA.query(include_goals=True)` will not see those goals.
4. **ADR-006** — OperatorKernel / alternate engines must not become intake; GoalEngine must not be quietly wired to `GOAL_SUBMIT_REQUEST`.
5. **ADR-016** — SA mutate must enter via scheduler callback, not repo-direct.

## Migration plan (ordered)

| Step | Action | Gate |
|------|--------|------|
| 1 | ✅ Inventory published | Doc honesty |
| 2 | ✅ Quarantine GoalEngine from live factory (#125) | R1.3 |
| 3 | ✅ **ADR-012 Accepted — Option A (retire)** | Human 2026-08-04 |
| 4 | Optional cleanup: archive/delete Phase-9 modules + `goal_engine_goals` | Separate PR |
| **5 ✅** | `SA.mutate` `submit_goal` via live SoT only | **ADR-016** |

**Hard rule (ADR-012 A):** no factory construction of GoalEngine onto intake; re-wire requires a new ADR. Schema drop is optional cleanup, not required for acceptance.

## Related shadow SoT

| Domain | Status |
|--------|--------|
| WM nodes/edges | ✅ SA mutate/query |
| Goals | ✅ Path A + A′ (ADR-016); Path B retired |
| Memory | ✅ 4a–4d (ADR-015) |
| Workflows / executions / agents | ⚠️ outside SA mutate |

## References

- `docs/architecture/adr/ADR-012_GOALS_PHASE9_DISPOSITION.md`
- `docs/architecture/adr/ADR-016_STATE_AUTHORITY_MUTATE_GOALS.md`
- `docs/architecture/SHADOW_SOT_INVENTORY.md`
- `docs/architecture/STATE_AUTHORITY_CONTRACT.md`
- `docs/architecture/GOAL_ENGINE.md`
- `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`
- `ai_command_center/core/service_factory.py`
- `ai_command_center/services/goal_scheduler_service.py`
- `ai_command_center/orchestration/goals/goal_engine.py`
