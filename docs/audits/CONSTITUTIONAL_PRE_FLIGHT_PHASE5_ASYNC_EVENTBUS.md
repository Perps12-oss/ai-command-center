# Constitutional Pre-Flight — Phase 5 Async EventBus

**Date:** 2026-08-07  
**Branch:** `cursor/phase5-async-eventbus-744e`  
**Authority:** `PROJECT_CONSTITUTION_V4.md` Art. X; `PERFORMANCE_CONSTITUTION.md` Art. VII/XII; `ASYNC_EVENTBUS_POLICY.md`  
**Gate clearance:** Human approval granted for Async EventBus (cloud task: “async bus approved”)

## Task Description

Complete Phase 5 Async EventBus exit criteria: implement `TieredDispatchPolicy`, multi-pool `AsyncDispatchQueue` (R4b/R4c/R4d), UCGS profile pool config, tests (classification / queue / shutdown / isolation / R4a latency gate), wire EventBus, update architecture and living-truth docs. Default bare `EventBus()` remains sync; application opt-in uses tiered dispatch.

## Authorities Reviewed

- `PROJECT_CONSTITUTION_V4.md` (Invariants 1, 3; Art. X–XIII)
- `PERFORMANCE_CONSTITUTION.md` (Art. IV budgets, VII investigation, X anti-patterns, XII escalation)
- `docs/architecture/ASYNC_EVENTBUS_POLICY.md`
- `docs/plans/PHASE_5_ASYNC_EVENTBUS_PLAN.md`
- `docs/governance/PHASE_COMPLETION_RULE.md`
- `docs/audits/R1_UNGATED_STOP_LINE.md`
- `AGENTS.md` ownership flow

## Files Reviewed

- `ai_command_center/core/event_bus.py`
- `ai_command_center/core/events/dispatch_policy.py`
- `ai_command_center/core/events/handler_dispatch.py`
- `ai_command_center/application.py`
- `tests/test_eventbus_*.py`
- `ucgs.profiles/ai-command-center.yaml`

## Protected Assets Impacted

| Asset | Impact |
|-------|--------|
| EventBus | Additive tiered multi-pool path; existing R4b single-queue + R4c adapters preserved |
| Topic registry | **No** membership change to `SYNC_CRITICAL` / `ASYNC_ELIGIBLE` sets |
| Dispatch policy budgets | Unchanged; pools route existing ASYNC_ELIGIBLE topics only |

## Sources of Truth Impacted

None. Dispatch policy is routing, not persistence or domain SoT.

## Architectural Invariants Impacted

| Invariant | Assessment |
|-----------|------------|
| 1 Ownership flow | Unchanged — still UI → AppState → EventBus → Services → Repositories → Storage |
| 3 EventBus governance | Strengthened — formal tiered policy + pools per Phase 5 plan |
| 13 Host supremacy | Unchanged |

## Contracts Impacted

- No versioned contract schema changes
- Feature flags: `EVENTBUS_TIERED_DISPATCH` (new); existing `EVENTBUS_DISPATCH_QUEUE` / `EVENTBUS_ASYNC_ADAPTERS` retained
- `create_application()` enables `tiered_dispatch=True` (approved)

## Gate Impact Assessment

| Gate | Effect |
|------|--------|
| Perf Art. VII/XII | Cleared by investigation report + human approval in this PR |
| Phase 5 exit 5.4 | Targeted by latency + regression tests |
| Arch lint / UCGS / constitution verify | Must PASS |

## Historical Gate Impact

Does not reopen PERF-001/002; does not change AppState coalesce; does not enable Goose / Predictive-Undo / OperatorKernel rewire.

## Regression Risk

| Risk | Mitigation |
|------|------------|
| Cross-pool reordering of unrelated topics | Documented; within-pool FIFO preserved |
| `dispatch_queue_depth` drain helpers | Aggregate depth across pools |
| SYNC_CRITICAL async bleed | Classification forces IMMEDIATE for SYNC_CRITICAL |
| Default test `EventBus()` behavior | Remains sync |

## Constitutional Status

**APPROVED** — implementation may proceed under explicit async-bus approval.
