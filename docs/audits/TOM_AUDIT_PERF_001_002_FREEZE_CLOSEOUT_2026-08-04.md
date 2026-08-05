# Tom Audit — Program 1 Freeze Side-Quest → PERF-001 / PERF-002

| Field | Value |
|---|---|
| **Auditor** | Tom (Senior Engineering Auditor) |
| **Date** | 2026-08-04 (rev 2 — audit self-correction) |
| **Scope tip** | `main` @ `c0dd1af` (merge #150) |
| **Scope chain** | #142 → #144 → #147 (freeze closeout) → #148 (PERF-001) → #150 (PERF-002) |
| **Baseline** | `PERFORMANCE_CONSTITUTION.md`, ADR-007, PERF_001/002 reports, RCA / baseline 2026-07-26 |
| **Method** | Source verification + targeted pytest; **no** Win ARM64 GUI soak; **no** before/after Tk timings |

### Audit errata (rev 1 → rev 2)

Rev 1 asserted six binary `PASS` labels beside a 78 / `PARTIALLY_IMPLEMENTED`
verdict, and treated “Constitution PASS” as process-following while the same
document said Art VI **Closed** DoD was unmet. That was inconsistent labeling,
not two independently derived assessments. Rev 2 separates **process** from
**outcome**, shows a deduction rubric, elevates the PerfInspector skip-path
defect to S1, grades the cited tests, and flags PERF-003 sequencing risk.

---

## Executive Summary

Agents largely followed the approved Program 1 *sequence* (side-quest → PERF-001
→ PERF-002, one bottleneck per PR, Optimization Ladder). PERF-001’s coalesce
path is implemented and headlessly reproducible. PERF-002’s **AppState fan-out
delete** for PerformanceInspector is real and valuable; its **fingerprint skip
under the 1 Hz timer is not** — `uptime_s` is inside the fingerprint
(`performance_inspector.py:107`), so every timer tick changes identity and
forces a full textbox rewrite. That is a **correctness defect against the
PERF-002 chosen-fix claim**, not cosmetic debt. Outcome verification for both
PRs’ purpose (runtime latency / freeze reduction) is **absent** from this audit
and from CI: no before/after GUI timings. Verdict remains
**PARTIALLY_IMPLEMENTED**, with a lower, rubric-backed score, and PERF-002’s
Art XV “Mitigated” status is **overstated for the PerformanceInspector skip
path** until that bug is fixed and soak data exists.

---

## Scores and status

```
Overall Score: 69
Status: PARTIALLY_IMPLEMENTED
Implementation Maturity: LEVEL_2–3 hybrid
  LEVEL_3 for PERF-001 headless coalesce contract
  LEVEL_2 for PERF-002 PerformanceInspector refresh-avoidance (fan-out fixed; skip path broken under timer)
```

### Why not COMPLIANT / why not 90+

Tom’s `COMPLIANT` floor is **90** and requires plan + architecture + quality
expectations met. Missing soak, missing GUI budgets, and a broken Perf skip
path under normal open-inspector use bar that floor. `PARTIALLY_IMPLEMENTED`
(65–89) is the correct band: features exist; significant portions incomplete or
weak.

### Rubric (visible formula)

Start at **100**. Deduct only what evidence supports:

| # | Deduction | pts | Axis |
|---|---|---:|---|
| D1 | Art VI soak / Art XV **Closed** unmet for PERF-001 and PERF-002 | −8 | Outcome / constitution DoD |
| D2 | No before/after GUI timing for either performance PR (budget claims unproven) | −7 | Outcome |
| D3 | PerfInspector fingerprint includes `uptime_s` → 1 Hz skip path effectively dead (`performance_inspector.py:94–107`, `_tick` at `:72–76`) | −8 | Outcome / PERF-002 correctness |
| D4 | PERF-002 report / Art XV language overclaims “met headless skip path” relative to Perf timer behavior | −3 | Honesty / plan claim |
| D5 | Weak / loose tests counting toward “23 passed” (see Test grading) | −3 | Evidence quality |
| D6 | Dead API (`timed_inspector_refresh`) + unused `_state_store` | −1 | Code quality |
| D7 | ADR-007 stale “docs-only” prose vs Status “Phase 3 landed” | −1 | Docs drift |

**100 − 8 − 7 − 8 − 3 − 3 − 1 − 1 = 69.**

No other deductions applied. Process adherence (ladder, one-PR, side-quest gate)
is credited by **not** taking further architecture/plan deductions.

### Dimension scores (weights from `tom-implementation-auditor.json`)

Scores chosen so **Σ(score × weight) / 100 = 69**, matching the deduction rubric
(not an independent second verdict).

| Dimension | Weight | Score | Contribution | Why this number |
|---|---:|---:|---:|---|
| architecture_compliance | 20 | 80 | 16.0 | Coalesce scoped; no SYNC/async default drift; residual amplifiers still live by design |
| plan_adherence | 15 | 65 | 9.75 | Sequence/ladder met; Art VI Closed + PERF-002 skip claim not met |
| implementation_completeness | 15 | 55 | 8.25 | PERF-001 solid; PERF-002 Perf skip broken; soak absent |
| code_quality | 15 | 78 | 11.7 | Clear structure; dead helper / unused store minor |
| maintainability | 10 | 76 | 7.6 | Shared helper OK; ADR drift |
| scalability | 5 | 74 | 3.7 | Chunk notify bounded; other topics unchanged |
| testability | 5 | 55 | 2.75 | Graded tests — count ≠ confidence |
| ui_consistency | 5 | 88 | 4.4 | CTk surfaces unchanged |
| performance | 5 | 40 | 2.0 | **Lowest** — purpose of PRs; no GUI Δ; Perf skip dead under timer |
| technical_debt | 5 | 57 | 2.85 | Mitigated label undermined by overclaim + open S1 defect |

**Σ contributions = 69.0** (= deduction rubric). Classification uses **69**.

---

## Compliance axes (rev 2 — not a single PASS table)

Binary `PASS` without scope is banned in this revision. Two axes:

### A. Process / pattern compliance (did agents follow the approved path?)

| Check | Result | Meaning |
|---|---|---|
| Program 1 fence | **PASS** | No Brain / UI redesign drift |
| Optimization Ladder order | **PASS** | Delete → avoid → coalesce |
| One bottleneck per PR | **PASS** | #148 then #150 |
| Side-quest before coalesce | **PASS** | #147 |
| AppState ownership preserved | **PASS** | Notify-only coalesce |
| CustomTkinter / no framework swap | **PASS** | |
| Primitive reuse (no parallel inspector stack) | **PASS** | |

### B. Outcome / constitution DoD compliance (did the fixes prove the budgets?)

| Check | Result | Meaning |
|---|---|---|
| Art VI soak test | **FAIL** | Not run / not evidenced |
| Art XV Closed | **FAIL** | Register still Mitigated |
| PERF-001 notify-rate outcome (headless) | **PASS** | Storm + tests support coalesce |
| PERF-001 UI-thread outcome (Win ARM64) | **UNPROVEN** | Operator |
| PERF-002 AppState fan-out delete | **PASS** | No `subscribe` in Perf `__init__` |
| PERF-002 fingerprint skip under 1 Hz timer | **FAIL** | `uptime_s` in fingerprint |
| Inspector refresh &lt;5 ms | **UNPROVEN** | No Tk wall-time evidence |

**Constitution Compliance (combined):** **CONDITIONAL / FAIL Closed-DoD** —
process PASS does **not** equal constitution PASS. Rev 1’s “Constitution
Compliance: PASS” was misleading and is **withdrawn**.

```
Constitution Compliance:     FAIL (Closed DoD) / PASS (process only) — see axes
Architecture Compliance:     PASS (structural; see Axis A)
Primitive Reuse Compliance:  PASS
CustomTkinter Compliance:    PASS
AppState Compliance:         PASS (structure) — outcome soak UNPROVEN
GitHub Pattern Compliance:   PASS
Outcome Verification:        FAIL / UNPROVEN for GUI budgets
```

---

## Critical finding (elevated)

### S1 — PerformanceInspector skip path defeated by design

**Severity: S1 (correctness vs declared PERF-002 fix), not S3 cleanup.**

Evidence:

1. Fingerprint **includes** `uptime_s` (`performance_inspector.py:107`).
2. Docstring admits intent: “excludes nothing the dump shows” (`:94`).
3. Refresh is driven by `_tick` every 1000 ms (`:72–76`) after AppState
   subscribe was removed (`:64–67`).
4. `uptime_s` is rounded to 0.1 s in `PerfMetrics.snapshot()` — a 1 s tick
   **always** advances displayed uptime → fingerprint inequality → full
   `delete`/`insert` (`:177–181` region).
5. The PERF-002 report lists “fingerprint + skip” as a chosen-fix pillar for
   PerformanceInspector; under the only automatic refresh path, skip does not
   fire.

**What still works:** Removing AppState subscription stops storm amplification
(delete unnecessary work). That alone is a real PERF-002 win.

**What does not work as claimed:** Avoid-duplicate rewrite under the timer.
Calling Art XV “Mitigated” for PERF-002 is acceptable **only if** scoped to
fan-out deletion; it is **not** acceptable as “inspector rebuild coalesce
complete” for the Perf window.

**Remediation (required before trusting Perf skip metrics):** Bucket or exclude
`uptime_s` from the equality fingerprint (still show live uptime in the dump if
desired via a cheap label update), or stop full textbox rebuild when only uptime
changed. Then measure `inspector.refresh.performance` skip vs rewrite rates with
the inspector open.

---

## Findings by severity

| Sev | Finding | Remediation class |
|---|---|---|
| **S1** | PerfInspector `uptime_s` fingerprint defeats 1 Hz skip | **Fix before claiming PERF-002 Mitigated for rebuild avoidance** |
| **S2** | No Win ARM64 soak / no GUI before-after for #148/#150 | Operator + measurement; blocks Art XV Closed |
| **S2** | PERF-003 sequencing while 001/002 soak + S1 open | See Sequencing risk |
| **S3** | `timed_inspector_refresh` unused; `_state_store` unused | Cleanup |
| **S3** | ADR-007 stale docs-only sentences; unchecked PR template boxes | Docs/process |
| **S3** | Coalesce test `<= 3` vs report’s `1`; source-string subscribe test | Tighten tests |

Rev 1 listed S1 beside dead code as “deficiency #1… small cleanup.” That
severity collapse is corrected here.

---

## Plan Adherence

| Plan step | Adherence |
|---|---|
| Freeze side-quest before ADR-007 coalesce (#147) | Met |
| Investigation report before fix | Met |
| One bottleneck per PR | Met |
| Ladder: delete / avoid / coalesce | **Partial** — delete (Perf unsubscribe) met; avoid (Perf skip under timer) **failed**; Runtime/Workspace fingerprints met |
| Art VI soak + Close debt | **Not met** |
| Inspector refresh &lt;5 ms | **Unproven** |

---

## Outcome verification (what this audit does *not* have)

These PRs exist to reduce runtime jank. This audit **does not** contain:

- Before/after UI-thread ms
- Before/after `inspector.refresh.*` distributions on Win ARM64
- Soak logs with `freeze_form=v6` under chat + open inspectors

Headless storm numbers for PERF-001 (100 chunks → coalesced/flush) are
**process-adjacent outcome** for notify *count*, not proof of frame-time relief.

**Do not read “23 tests passed” as outcome verification.** See grading below.

---

## Test grading (of the 23 cited)

| Bucket | Count (approx) | Trust | Notes |
|---|---:|---|---|
| PERF-001 coalesce / env / metrics behavior | ~7 | **High** for notify-count contract | Still allows `<= 3` in one assertion vs report’s exact 1 — slight looseness |
| PERF-002 fingerprint equality (Runtime/Workspace/Orch/Perf static fp) | ~7 | **Medium** | Correct for identity math; **does not** prove Tk &lt;5 ms or timer skip |
| PERF-002 “no subscribe” via `inspect.getsource` | 1 | **Low** | String absence ≠ runtime subscription probe |
| Freeze closeout / runtime identity | ~7 | **Medium** | Adjacent; not PERF-001/002 outcome |
| Metrics helper smoke | ~1 | Low–medium | Observation only |

**Effective high-trust tests toward stated performance outcomes: roughly 6–8 of 23.**
The audit may cite the suite as “contracts green,” not as “budgets met.”

---

## Sequencing risk (PERF-003)

Rev 1 greenlit PERF-003 while saying “don’t reopen 001/002 without soak.” That
under-specified interaction risk.

**Flag:** PERF-003 (`settings.snapshot` / OpenAI sync handler) shares the same
UI-thread / EventBus sync surface as the unsoaked PERF-001/002 work. Starting
003 is **allowed by the one-bottleneck rule** (different debt ID), but:

1. Fix **S1 Perf skip** first or in the same small patch train — otherwise open
   Perf Inspector during 003 soak will still rewrite every second and confound
   “is 003 better?” readings.
2. Do **not** interpret a green 003 PR as closing 001/002.
3. Prefer a short Win ARM64 baseline *before* or *with* 003 kickoff: notify rates
   + `inspector.refresh.*` with Runtime/Perf open — even a 10-minute soak beats
   another unmeasured merge.

If 003 lands without that, residual freezes will be mis-attributed.

---

## Architecture Compliance (structural)

Unchanged positive findings: coalesce only on `{CHAT_CHUNK}`; reducers every
chunk; no SYNC_CRITICAL / async EventBus default changes; inspectors remain
read-only CTk surfaces.

## Evidence

**Read:** Constitution Art VI–VIII/XIII/XV; ADR-007; PERF_001/002 reports;
`app_state.py` coalesce; four inspectors; `inspector_refresh.py`; tests above.

**Ran (contracts only):**
```text
APPDATA=/tmp/aicc_appdata python3 -m pytest \
  tests/test_perf002_inspector_fingerprints.py \
  tests/test_appstate_notify_coalesce.py \
  tests/test_appstate_notify_metrics.py \
  tests/test_ui_freeze_closeout_fingerprints.py \
  tests/test_runtime_identity.py -q --no-cov
→ 23 passed  (see Test grading — not budget proof)
```

**Not run / not available to this auditor:** Win ARM64 GUI soak; before/after
frame or inspector refresh timings for #148/#150.

**Commits on tip:** `c32bf07` (#147), `450d8fb` (#148), `4e2a012` (#150), merge `c0dd1af`.

---

## Risk Assessment

| Horizon | Risk |
|---|---|
| Short-term | Treating Art XV “Mitigated” + rev-1 PASS table as “freeze fixed”; Perf Inspector open during chat still pays full rebuild/sec |
| Sequencing | PERF-003 work confounded by unbroken Perf timer rebuilds and unsoaked 001/002 |
| Long-term | Pseudo-precise audit scores without rubrics (rev 1) train false confidence — corrected here |

---

## Next actions (ordered, severity-aligned)

1. **S1 fix:** Exclude or bucket `uptime_s` (and optionally isolate volatile
   counters) so PerfInspector skip can fire on the 1 Hz path; add a test that
   identical non-uptime fingerprints skip / that timer-relevant fps differ only
   when non-uptime fields change.
2. **Measure:** Win ARM64 soak with Runtime + Perf open — record
   `inspector.refresh.*.skipped` vs timed rebuilds and notify rates; only then
   consider Art XV Closed language.
3. **Tighten tests:** Replace `inspect.getsource` subscribe check with a
   behavioral probe; document or tighten coalesce `<= 3` bound.
4. **Docs:** Scrub ADR-007 stale docs-only lines; narrow PERF-002 “Mitigated”
   wording to fan-out delete until S1 is fixed.
5. **PERF-003:** May start as next debt ID **after** S1 fix (or tightly coupled
   patch), with explicit note that 001/002 soak remains open — do not use 003
   merges as proxy closeout for 001/002.

---

## Final Verdict

**PARTIALLY_IMPLEMENTED — score 69 (rubric above).**

- Agents’ **process** adherence: largely good.
- **Outcome** adherence to constitution budgets: unproven; Perf skip path **fails**
  under its primary timer.
- Merges on `main` remain historically justified as incremental mitigations.
- Rev 1’s all-PASS compliance block and soft treatment of `uptime_s` are
  **rescinded**. Do not close PERF-001/002 and do not treat PERF-002 rebuild
  avoidance as done until S1 is fixed and GUI evidence exists.
