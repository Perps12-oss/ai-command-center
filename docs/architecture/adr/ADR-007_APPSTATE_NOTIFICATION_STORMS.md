# ADR-007: AppState Notification Storms — First Program 1 Investigation

**Status:** Proposed / Investigation (Phase 2 instrumentation approved)  
**Date:** 2026-07-26  
**Deciders:** Project owner (approval required before behavior-changing implementation)  
**Related:** `PERFORMANCE_CONSTITUTION.md`, `docs/audits/PERF_BASELINE_REPORT_2026-07-26.md`, `docs/audits/PERFORMANCE_RCA_UI_FREEZE_2026-07-24.md`, `ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`

### Phase 2 metric keys (observation only — no behavior change)

| Key | Meaning |
|---|---|
| `appstate.notify` | Timing sample: wall ms for listener fan-out (budget &lt;1 ms) |
| `appstate.notify` (counter) | Number of notify passes that invoked ≥1 listener |
| `appstate.notify.topic.<topic>` | Notify passes by topic |
| `appstate.notify.listener_invocations` | Sum of listeners called |
| `appstate.notify.skipped.metrics_only` | Dirty `system.snapshot` skipped (metrics-only delta) |
| `appstate.notify.skipped.no_listeners` | Dirty update with zero subscribers |

Phase 3 fix remains **blocked** until an Investigation Report with these metrics is approved.

---

## Context

Program 1 prioritizes runtime responsiveness. All UI pressure eventually flows through `AppStateStore` (`ai_command_center/core/app_state.py`).

Current mitigations on tip (`5cef96b` / #110):

- Topic → reducer index (not all 78 reducers on every event)
- Identity dirty detection (`nxt is not new_state`)
- Metrics-only `system.snapshot` skips listener notify
- Inspector fingerprint coalesce; stream-only UI apply path

Residual risk:

- When notify fires, **listeners still run inline on the publish/dispatch thread**
- Dual projection (AppState listener + EventCoordinator) can amplify refresh
- Headless baseline shows high-frequency reduce sources (`chat.chunk`, `service.*`, `system.snapshot`) but **UI notify rate is not yet a first-class metric** (0 listeners without Tk shell)

This ADR locks the **first investigation target**. It does **not** authorize a code fix.

---

## Decision

1. The first Program 1 investigation is **AppState notification storms** (PERF-001).
2. Investigation order remains: AppState storms → Inspector rebuilds → Navigation → SQLite contention → SYNC_CRITICAL *work* reduction.
3. Work stays analysis / documentation until an Investigation Report is approved.
4. Do **not** change `SYNC_CRITICAL` topic membership in this investigation.
5. Do **not** enable `EVENTBUS_DISPATCH_QUEUE` / `EVENTBUS_ASYNC_ADAPTERS` by default.
6. Future fix PRs fix **exactly one** bottleneck and include before/after measurements.

---

# Performance Investigation Report (template filled — investigation stage)

```text
# Performance Investigation Report

Problem
--------
User-visible risk: UI jank / freeze pressure from frequent AppState updates
faning out to shell apply and open inspectors (RCA ranks 6–10; residual after #110).

Evidence
--------
- PERF_BASELINE_REPORT_2026-07-26: AppState reduce avg 0.040 ms (under budget),
  but top reduce volumes: chat.chunk (100), service.state_changed (82),
  system.snapshot (42) in a short synthetic workload.
- Headless listener_count = 0 → UI notify storms not directly measured yet.
- RCA + PERF_ARCHITECTURE_EVIDENCE: metrics-only snapshot skip and reducer index
  landed; listener notify still inline; dual projection remains.
- Gap: no appstate.notify count/timing in PerfMetrics today.

Call Chain
----------
EventBus.publish(topic)
  → AppStateStore._on_event (indexed reducers, identity dirty)
  → if dirty and not metrics-only SYSTEM_SNAPSHOT skip:
       for listener in listeners: listener(new_state)   # inline
  → UIController / shell StateApplier._queue_state_refresh
  → (optional) inspectors refresh
  → (parallel) EventCoordinator may also schedule UI refresh for some topics

Ownership
---------
Program 1 (Runtime)

Root Cause
----------
(Investigation hypothesis — not yet proven as sole cause)
High-frequency dirty AppState updates × N listeners × inline notify on the
publish thread amplify into UI apply / inspector work. Reduce cost alone is
not the freeze; notify fan-out + listener work is the suspected amplifier.

Alternative Causes
------------------
1. Inspector rebuild cost dominates (PERF-002) even at modest notify rates.
2. Dual EventCoordinator + AppState refresh schedules duplicate UI work.
3. Chat chunk / string-buffer growth dominates during streams.
4. settings.snapshot heavy handlers (PERF-003) dominate interactive stalls
   (measured max 82 ms) — separate issue, not first in order.
5. Navigation _show_view pack churn (PERF-004) — later in order.

Chosen Fix
----------
Deferred. This ADR authorizes investigation + instrumentation proposal only.
Likely Optimization Ladder entry points (post-approval):
  1) Delete unnecessary notifies
  2) Avoid duplicate listener work
  3) Coalesce notifies / UI apply
— not “new abstraction” or SYNC_CRITICAL reclassification.

Why this fix?
-------------
N/A until Phase 2 measurements confirm notify fan-out as the bottleneck.
Ladder forbids jumping to parallelize/micro-optimize first.

Blast Radius
------------
If a future fix is approved, expected touch set (estimate only):
  - ai_command_center/core/app_state.py
  - ai_command_center/core/perf/metrics.py (notify counters)
  - possibly ai_command_center/ui/shell/state_applier.py
  - possibly inspectors (PERF-002 — separate PR)
Out of bounds for this investigation’s eventual fix PR:
  - dispatch_policy SYNC_CRITICAL set
  - ExecutionAuthority intake redesign
  - SQLite schema
  - Brain / Program 2 modules

Success Criteria
----------------
Before any fix merges:
  - appstate.notify count + timing exist in PerfMetrics (Phase 2)
  - Reproduced storm under controlled workload with before numbers
After fix (Phase 3, separate PR):
  - Notify rate and/or listener cost reduced vs baseline
  - AppState reduce/notify/UI apply budgets held
  - Headless perf tests green
  - Win ARM64 soak with freeze_fix=v5 shows no regression

Rollback
--------
This docs-only ADR: revert the markdown commit.
Future code fix: revert that single-purpose PR; feature flags preferred if risk high.
```

---

## Alternatives considered (investigation priority)

| Alternative | Why not first |
|---|---|
| Start with SYNC_CRITICAL topic changes | Higher-risk architectural change; out of bounds initially |
| Enable EventBus async flags by default | Explicitly forbidden without approval |
| Fix tool-executor sync `communicate` | Non-goal unless profiling proves freeze contribution |
| Start with SQLite / inspectors / navigation | Lower leverage than AppState fan-out per Program 1 order |

---

## Consequences

### Stop

- Implementing AppState notify coalescing / listener changes before Investigation Report approval and Phase 2 metrics
- Broad “AppState refactor” PRs
- Combining PERF-001 with PERF-002/003/004 in one PR

### Continue

1. Land `PERFORMANCE_CONSTITUTION.md` + this ADR + baseline report (docs PR)
2. Phase 2: instrumentation only (`appstate.notify` etc.) — separate PR after approval
3. Phase 3: one approved bottleneck fix with before/after

---

## Rollback

Revert this ADR file / mark Status superseded if investigation redirects. No runtime behavior is changed by accepting this ADR in Proposed/Investigation status.
