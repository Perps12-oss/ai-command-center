# ADR-007: AppState Notification Storms — First Program 1 Investigation

**Status:** Accepted — Phase 3 fix landed (`chat.chunk` notify coalesce)  
**Date:** 2026-07-26 (updated 2026-08-04)  
**Deciders:** Project owner  
**Related:** `PERFORMANCE_CONSTITUTION.md`, `docs/audits/PERF_001_INVESTIGATION_REPORT.md`, `docs/audits/PERF_BASELINE_REPORT_2026-07-26.md`, `docs/audits/PERFORMANCE_RCA_UI_FREEZE_2026-07-24.md`, `ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`

### Phase 2 metric keys (observation)

| Key | Meaning |
|---|---|
| `appstate.notify` | Timing sample: wall ms for listener fan-out (budget &lt;1 ms) |
| `appstate.notify` (counter) | Number of notify passes that invoked ≥1 listener |
| `appstate.notify.topic.<topic>` | Notify passes by topic |
| `appstate.notify.listener_invocations` | Sum of listeners called |
| `appstate.notify.skipped.metrics_only` | Dirty `system.snapshot` skipped (metrics-only delta) |
| `appstate.notify.skipped.no_listeners` | Dirty update with zero subscribers |
| `appstate.notify.coalesced` | Stream chunks absorbed into pending coalesce window |
| `appstate.notify.flush` | Coalesce timer delivered a fan-out |

### Phase 3 fix (2026-08-04)

Trailing-edge coalesce for `chat.chunk` notifies only (default 40 ms;
`APPSTATE_NOTIFY_COALESCE_MS=0` disables). Evidence:
`docs/audits/PERF_001_INVESTIGATION_REPORT.md` (100 chunk notifies → 1).

Phase 2 instrumentation remains required for any further PERF-001 work.


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
Phase 3 (2026-08-04): trailing-edge coalesce of `chat.chunk` AppState listener
notifies (40 ms; `APPSTATE_NOTIFY_COALESCE_MS`). Reducers unchanged.
See `docs/audits/PERF_001_INVESTIGATION_REPORT.md` for before/after.

Why this fix?
-------------
Phase 2 storm showed 100/100 notifies from `chat.chunk` while notify avg ≪1 ms.
Ladder step: coalesce notifies (not SYNC_CRITICAL changes, not new abstractions).

Blast Radius
------------
Touch set:
  - ai_command_center/core/app_state.py (coalesce)
  - ai_command_center/core/perf/metrics.py (counters already generic)
  - docs/audits/PERF_001_INVESTIGATION_REPORT.md
Out of bounds (honored):
  - dispatch_policy SYNC_CRITICAL set
  - ExecutionAuthority intake redesign
  - SQLite schema
  - Brain / Program 2 modules

Success Criteria
----------------
Before fix: appstate.notify* metrics + storm numbers recorded.
After fix: chat.chunk notifies 100 → 1 in same storm; coalesce counters live;
headless tests green. Win ARM64 soak remains operator closeout.

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

- Broad “AppState refactor” PRs
- Combining PERF-001 with PERF-002/003/004 in one PR
- Changing SYNC_CRITICAL membership or enabling async EventBus flags by default

### Continue

1. Win ARM64 soak to fully close PERF-001 debt register row
2. PERF-002 Inspector rebuilds (next in Program 1 order)
3. Keep `APPSTATE_NOTIFY_COALESCE_MS=0` as rollback

---

## Rollback

Revert this ADR file / mark Status superseded if investigation redirects. No runtime behavior is changed by accepting this ADR in Proposed/Investigation status.
