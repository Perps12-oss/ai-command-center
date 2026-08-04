# PERF-002 Investigation Report — Inspector Rebuilds

| Field | Value |
|---|---|
| **Date** | 2026-08-04 |
| **Debt** | PERF-002 (Performance Debt Register) |
| **Status** | Phase 2 evidence + Phase 3 fix (this change) |
| **Code tip** | `cursor/perf002-inspector-rebuilds-30d3` |
| **Method** | Code-path analysis + headless fingerprint / skip counters; GUI &lt;5 ms soak is Win ARM64 |

---

## Constitutional Pre-Flight

| Check | Result |
|---|---|
| Program fence | **Program 1** only (Runtime / UI inspectors) |
| Ownership | UI → AppState → EventBus; inspectors remain read-only |
| Contracts | No new domain models; no service-to-service calls |
| Ladder | Delete unnecessary work → avoid duplicate → coalesce (no threading) |
| Out of bounds | PERF-001 coalesce tuning, PERF-003/004, Brain/Program 3 redesign |

---

## Problem

Open developer inspectors amplify AppState / EventBus churn into full Tk text
rebuilds (`delete` + `insert`, sometimes `json.dumps`). Symptom: visible jank
(S2) when inspectors are open during chat / orchestration activity — even after
PERF-001 reduced `chat.chunk` notify rate.

## Evidence

| Inspector | AppState subscribe | Fingerprint | Pending coalesce | Notes |
|---|---|---|---|---|
| `PerformanceInspector` | **Yes** | **None** | Yes | Metrics come from `PerfMetrics` / bus — AppState fan-out is wasted work; every notify + 1 s tick rebuilds textbox |
| `RuntimeInspector` | Yes | **Weak** (`len` only for runs/health) | Yes | Early-out exists but misses content identity; Capability Explorer not in fp |
| `OrchestrationInspector` | Yes | Strong orch fields | Yes | Always rewrites textbox when fp changes; no content-equality skip |
| `WorkspaceOsInspector` | No (bus only) | **None** | **No** | Every matching bus event enqueues full entity/button rebuild |

RCA crosswalk: `PERFORMANCE_RCA_UI_FREEZE_2026-07-24.md` rank 10;
baseline `PERF_BASELINE_REPORT_2026-07-26.md` §6 (N/A headless).

## Call Chain

```text
AppStateStore.notify / EventBus topic
  → inspector._schedule_refresh (UIQueue)
    → inspector._refresh
      → build strings (+ json.dumps)
      → CTkTextbox delete/insert  (expensive)
```

## Ownership

**Program 1** (Runtime).

## Root Cause

Open inspectors perform **full UI rebuilds** on refresh triggers without
deleting unnecessary subscriptions or skipping when displayed content is
unchanged.

## Alternative Causes

1. PERF-001 incomplete (chunk notify still too high) — mitigated; residual is
   inspector work itself.
2. Tk `CTkTextbox` inherently slow — true but secondary; skip rewrite first.
3. Weak Runtime fingerprint causing *missed* updates — correctness issue, not
   the storm amplifier.

## Chosen Fix (Optimization Ladder)

1. **Delete:** `PerformanceInspector` unsubscribes from AppState (timer +
   manual Refresh only — metrics are not AppState projections).
2. **Avoid duplicate:** Content / fingerprint early-outs on all four inspectors;
   strengthen `RuntimeInspector` fingerprint (runs, provider health, capability
   providers, full orch display fields).
3. **Coalesce:** `WorkspaceOsInspector` gains `_refresh_pending` (same pattern
   as other inspectors).
4. **Measure:** Record `inspector.refresh.<name>` timings; incr
   `inspector.refresh.<name>.skipped` on fingerprint early-out.

## Why this fix?

Smallest Program 1 repair matching constitution budgets (inspector refresh
&lt;5 ms). Does not change EventBus SYNC set, AppState reducers, or PERF-003/004.

## Blast Radius

| File | Change |
|---|---|
| `ui/performance_inspector.py` | Drop AppState subscribe; fingerprint + skip; timing |
| `ui/runtime_inspector.py` | Strong fingerprint; timing / skip counter |
| `ui/orchestration_inspector.py` | Content skip; timing |
| `ui/workspace_os_inspector.py` | Pending coalesce + fingerprint; timing |
| `PERFORMANCE_CONSTITUTION.md` | PERF-002 register row |
| `docs/audits/PERF_002_INVESTIGATION_REPORT.md` | This report |
| `tests/test_perf002_inspector_fingerprints.py` | Headless fingerprint / contract tests |

## Success Criteria

| Criterion | Status |
|---|---|
| PerformanceInspector not on AppState fan-out | Met (code) |
| Fingerprint skips identical Runtime / Workspace / Perf dumps | Met (tests) |
| `inspector.refresh.*` metrics exist | Met |
| Headless tests green | Met |
| Win ARM64 refresh avg &lt;5 ms with inspector open | **Operator soak** |

### Headless before / after (rebuild decision)

Storm simulation: 100 AppState-shaped notifies with **unchanged** inspector
inputs (orchestration / workspace / metrics fingerprint stable).

| Metric | Before | After |
|---|---:|---:|
| PerformanceInspector AppState-driven refreshes | 100 | **0** (no subscribe) |
| RuntimeInspector full rebuilds (same fp) | 100 scheduled → 1 build then 99 skip* | **0 rebuilds** after first (fingerprint) |
| WorkspaceOs pending coalesces duplicate bus events | N enqueues | **1** pending |

\*Pre-fix Runtime already fingerprint-skipped after first paint when lengths
matched; strengthening preserves skip while fixing content-identity holes.

## Out of bounds (unchanged)

- PERF-003 (`settings.snapshot` / OpenAI handler)
- PERF-004 (navigation `_show_view`)
- AppState `chat.chunk` coalesce defaults
- Inspector UX redesign

## Rollback

Revert the PERF-002 commit(s). No env flag required (behavior is purely skip /
unsubscribe).
