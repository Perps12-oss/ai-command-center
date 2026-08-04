# Tom Audit — Program 1 Freeze Side-Quest → PERF-001 / PERF-002

| Field | Value |
|---|---|
| **Auditor** | Tom (Senior Engineering Auditor) |
| **Date** | 2026-08-04 |
| **Scope tip** | `main` @ `c0dd1af` (merge #150) |
| **Scope chain** | #142 → #144 → #147 (freeze closeout) → #148 (PERF-001) → #150 (PERF-002) |
| **Baseline** | `PERFORMANCE_CONSTITUTION.md`, ADR-007, PERF_001/002 reports, RCA / baseline 2026-07-26 |
| **Method** | Source verification + targeted pytest (23 passed); no Win ARM64 GUI soak |

---

## Executive Summary

Coding agents delivered the approved Program 1 sequence for AppState notification
storms (PERF-001) and inspector rebuilds (PERF-002), after a freeze side-quest
closeout that correctly blocked coalesce work until identity/fingerprint leftovers
landed. Headless code and tests match the investigation reports and Optimization
Ladder (delete → avoid duplicate → coalesce). **Do not treat debt items as Closed:**
Art XV still says Mitigated; Win ARM64 soak and the &lt;5 ms Tk refresh budget are
**unproven**. PerformanceInspector’s fingerprint includes `uptime_s`, so the 1 Hz
timer almost always rewrites the textbox — fan-out delete is real; Perf skip-path
claims are overstated. Verdict: **PARTIALLY_IMPLEMENTED** relative to full
constitution DoD; **acceptable as Mitigated** relative to declared Phase 3 scope.

---

## Scores and status

```
Overall Score: 78
Status: PARTIALLY_IMPLEMENTED
Implementation Maturity: LEVEL_3 (Feature complete headless; production soak open)
```

### ACC final verdict block

```
Constitution Compliance:     PASS  (Program fence + ladder; closeout honesty preserved)
Architecture Compliance:     PASS  (AppState / EventBus / UI render path intact)
Primitive Reuse Compliance:  PASS  (dev inspectors repaired, not duplicated)
CustomTkinter Compliance:    PASS  (no framework substitution)
AppState Compliance:         PASS  (coalesce on notify only; reducers unchanged)
GitHub Pattern Compliance:   PASS  (pattern adaptation, not clone)
```

---

## Dimension scores (weighted)

| Dimension | Weight | Score | Notes |
|---|---:|---:|---|
| architecture_compliance | 20 | 88 | Coalesce scoped to `chat.chunk`; inspectors remain AppState/bus readers |
| plan_adherence | 15 | 82 | Matches ADR-007 Phase 3 + PERF-002 chosen fix; Art VI soak incomplete |
| implementation_completeness | 15 | 72 | Code + headless tests done; operator soak / Tk budget unproven |
| code_quality | 15 | 80 | Clear metrics; unused `timed_inspector_refresh` + unused Perf `state_store` |
| maintainability | 10 | 78 | Shared `inspector_refresh` helper; ADR Status vs stale “docs-only” prose |
| scalability | 5 | 75 | Chunk coalesce scales notify rate; other topics still 1:1 |
| testability | 5 | 70 | Fingerprint/coalesce contracts good; GUI timing absent; source-string subscribe test weak |
| ui_consistency | 5 | 85 | CTk inspectors unchanged visually |
| performance | 5 | 68 | Headless storm numbers match report; budget claims overreach without GUI |
| technical_debt | 5 | 74 | Honest Mitigated status; residual PERF-003–005 open |

**Weighted overall ≈ 78.**

---

## Mandatory ACC questions

1. **Reuse existing primitives?** Yes — repaired existing inspectors / AppStateStore; no parallel notify bus.
2. **Duplicate functionality?** No new inspector framework; one shared timing helper (partially unused).
3. **Match approved ACC design?** Yes for Program 1 runtime repair.
4. **AppState driven?** Yes for Runtime/Orchestration; Perf correctly *removed* AppState fan-out (metrics not AppState).
5. **CustomTkinter native?** Yes.
6. **Repository patterns?** Yes (`UIQueue`, fingerprints, PerfMetrics).
7. **Scale without rewrite?** Yes for stream notify; settings/nav debt remains (PERF-003/004).
8. **Senior eng production approve?** Approve merge as Mitigated; **do not** close Art XV without Win soak.

---

## Architecture Compliance

- Ownership UI → AppState → EventBus preserved.
- PERF-001 changes only listener fan-out scheduling (`_NOTIFY_COALESCE_TOPICS`,
  `_schedule_coalesced_notify` / `_flush_coalesced_notify` in
  `ai_command_center/core/app_state.py:264-278`, `3750-3795`).
- Reducers still run every `chat.chunk` (reduce before coalesce branch).
- No SYNC_CRITICAL membership change; no EventBus async default flip — matches
  ADR-007 out-of-bounds.
- PERF-002 stays in UI inspector modules; no service-layer rewrite.

## Plan Adherence

| Plan step | Agent adherence |
|---|---|
| Freeze side-quest before ADR-007 coalesce (#147) | Met (`c32bf07`; stop before PERF-001) |
| Investigation report before fix | Met (PERF_001 / PERF_002 reports on main) |
| One bottleneck per PR | Met (#148 then #150) |
| Ladder: delete / avoid / coalesce | Met (Perf unsubscribe; fingerprints; pending coalesce) |
| Art VI soak + Close debt | **Not met** — status remains Mitigated + operator |
| Inspector refresh &lt;5 ms | **Claimed via skip path only** — not measured on Tk |

## Repository Pattern Adherence

Matches existing fingerprint / `UIQueue` / PerfMetrics patterns from freeze
closeout (#147) and state applier. No React/web substitute.

## Implementation Findings

### PERF-001 (met in code)

- Default 40 ms; `APPSTATE_NOTIFY_COALESCE_MS=0` disables
  (`notify_coalesce_ms_from_env`, `app_state.py:270-278`).
- Metrics: `appstate.notify.coalesced`, `.flush`, topic counters.
- Ad-hoc + tests: 100 chunks → 1 topic notify + coalesced/flush (report aligned).
- Identity: `freeze_fix=v6`; coalesce flag logged from UI app.

### PERF-002 (mostly met; one weak claim)

- PerformanceInspector: no `subscribe` (`performance_inspector.py:64-67`); timer + Refresh.
- Runtime fingerprint: content tuples, not `len(...)` (`runtime_inspector.py:143-183`).
- Workspace: `_refresh_pending` + fingerprint.
- Orchestration: fingerprint + `_last_content` skip.
- Metrics: `inspector.refresh.<name>` / `.skipped` via `inspector_refresh.py`.

### Deficiencies (line-level)

1. **`performance_inspector.py` fingerprint includes `uptime_s`** — 1 s tick forces
   nearly every refresh to rebuild text; skip counter rarely increments in real use.
   Tests encode this (`tests/test_perf002_inspector_fingerprints.py` uptime 1≠2).
2. **`inspector_refresh.timed_inspector_refresh`** — defined, zero call sites (dead API).
3. **`PerformanceInspector._state_store`** — still assigned, never read (API inertia).
4. **`test_performance_inspector_does_not_subscribe_to_appstate`** — `inspect.getsource`
   string check, not behavioral subscription probe
   (`tests/test_perf002_inspector_fingerprints.py:24-28`).
5. **Coalesce test allows `<= 3` notifies** — loose vs report’s exact 1
   (`tests/test_appstate_notify_coalesce.py`); storm repro can still hit 1.
6. **ADR-007 stale prose** — Status says Phase 3 landed; Context/Rollback still say
   docs-only / does not authorize fix (documentation drift).
7. **PR templates #148/#150** — constitutional checkboxes left unchecked (process debt).

## Code Quality Findings

Clear comments tying changes to PERF IDs. Shared helper is thin and appropriate.
Dead helper and unused ctor dependency should be cleaned in a follow-up, not a redo.

## Technical Debt

| Item | Severity | Notes |
|---|---|---|
| Win ARM64 soak PERF-001/002 | S2 process | Blocks Art XV Closed |
| PERF-003 settings.snapshot handler | S1 open | Next Program 1 gate |
| PERF-004 navigation `_show_view` | S2 open | |
| PERF-005 SQLite contention | S2 open | |
| PerfInspector uptime-in-fingerprint | S3 | Dilutes PERF-002 skip claim for Perf window |
| Unused `timed_inspector_refresh` | S3 | Delete or adopt |

## Partially Implemented Features

- Art VI Definition of Done (soak / close register) for PERF-001 and PERF-002.
- PerformanceInspector rebuild avoidance under timer (fan-out fixed; rewrite not).
- GUI budget proof for inspector refresh &lt;5 ms.

## Features Requiring Redesign

**None.** Do not rewrite AppState or invent a new inspector framework. Patch forward:
exclude `uptime_s` from Perf fingerprint (or bucket it), tighten tests, run soak.

## Evidence

**Read:** Constitution Art VI–VIII/XIII/XV; ADR-007; PERF_001/002 reports; baseline/RCA;
`app_state.py` coalesce; four inspectors; `inspector_refresh.py`; coalesce + fingerprint tests.

**Ran:**
```text
APPDATA=/tmp/aicc_appdata python3 -m pytest \
  tests/test_perf002_inspector_fingerprints.py \
  tests/test_appstate_notify_coalesce.py \
  tests/test_appstate_notify_metrics.py \
  tests/test_ui_freeze_closeout_fingerprints.py \
  tests/test_runtime_identity.py -q --no-cov
→ 23 passed
```

**Not run:** Win ARM64 GUI soak / Performance Inspector live timings.

**Commits verified on tip:** `c32bf07` (#147), `450d8fb` (#148), `4e2a012` (#150), merge `c0dd1af`.

## Risk Assessment

| Horizon | Risk |
|---|---|
| Short-term | Operators may believe PERF-001/002 are “done”; residual jank from PERF-003/004 or open Perf timer rewrite |
| Long-term | Debt register honesty is good; overstated “met headless” budget language trains false confidence |

## Next actions (ordered)

1. Operator: Win ARM64 soak — `freeze_form=v6`, open Runtime + Perf inspectors under chat; record `inspector.refresh.*` / notify rates; only then set Art XV to Closed.
2. Small follow-up: exclude or bucket `uptime_s` in PerformanceInspector fingerprint; delete or use `timed_inspector_refresh`; drop unused `_state_store` or document retained API.
3. Tighten coalesce test to exact flush semantics (or document timing flake bound).
4. Scrub ADR-007 stale “docs-only” sentences.
5. Proceed to **PERF-003** (`settings.snapshot` / OpenAI handler) as next single bottleneck — do not reopen PERF-001/002 architecture without soak evidence.

## Final Verdict

**PARTIALLY_IMPLEMENTED (78)** — agents adhered to Program 1 plans and architecture for
the declared Phase 3 fixes. Merges on `main` are justified. Constitution DoD for
**Closed** debt is **not** satisfied. Approve as **Mitigated**; withhold **Closed**
and any “UI freeze fully solved” claims until Win ARM64 evidence exists.
