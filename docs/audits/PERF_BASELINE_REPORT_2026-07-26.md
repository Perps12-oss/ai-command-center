# Performance Baseline Report

| Field | Value |
|---|---|
| **Date** | 2026-07-26 |
| **Git tip** | `5cef96b` (`perf(architecture): slice AppState, async telemetry, kill UI sync debt (#110)`) |
| **Freeze fingerprint target** | `ACC_UI_RUNTIME freeze_fix=v5` |
| **Method** | Headless `create_application()` + `PerfMetrics` workload; CI pytest; RCA crosswalk |
| **Environment** | Linux x86_64 (Cloud agent). GUI is Windows-ARM64 only — UI thread / Tk view-switch / inspector refresh **not measurable here**. |
| **Raw JSON** | [`PERF_BASELINE_2026-07-26.json`](PERF_BASELINE_2026-07-26.json) |
| **Purpose** | Phase 0 “before” snapshot. No product code changed for this report. |

---

## Constitutional Pre-Flight (docs-only follow-on)

1. **Constitution:** `PROJECT_CONSTITUTION_V4.md` remains supreme; this baseline does not alter architecture.
2. **Architecture:** Runtime spine (EventBus → AppState → UIQueue) unchanged.
3. **Contracts:** No contract changes.
4. **Verdict:** Safe to proceed to docs-only constitution + ADR PR after this baseline.

---

## 1. Budgets vs actual (headless)

| Budget | Target | Actual (this run) | Status |
|---|---|---|---|
| AppState reducer avg | &lt;0.5 ms (constitution) / &lt;2 ms CI mean | **avg 0.040 ms**, max 0.163 ms (n=350) | PASS headless |
| EventBus sync handler | &lt;5 ms | Most &lt;1 ms; **`settings.snapshot` avg 7.50 ms, max 82.23 ms** | FAIL (handler budget) |
| EventBus publish (UI_NAVIGATE ×30) | &lt;60 ms total CI | **0.32 ms total** | PASS headless |
| UI_COMMAND publish mean | &lt;16 ms CI | **mean 0.25 ms**, max 0.68 ms | PASS headless |
| Settings snapshots / set | 1 | **1** | PASS |
| UI thread avg / P99 | &lt;2 ms / &lt;8 ms | **N/A** (no Tk) | Deferred to Win ARM64 |
| Navigation view switch | &lt;16 ms | **N/A** (publish only measured) | Deferred to Win ARM64 |
| Inspector refresh | &lt;5 ms | **N/A** | Deferred to Win ARM64 |
| SQLite on UI thread | Never | **N/A** headless; telemetry batch async off publish path | Partial |
| EventBus queue depth | &lt;100 | **0** (`_dispatch_queue`; async defaults OFF) | PASS |

### Workload notes

- 30× `ui.navigate`, 8× `ui.command`, 40× `system.snapshot`, 100× `chat.chunk`, 1× settings set.
- Storm rate guards logged: `ui.navigate storm ... rate=5/s` then `20/s` (expected under synthetic burst; guards active).
- Logged budget breach: `OpenAIHttpService._on_settings_snapshot` **82.23 ms** vs **5 ms** SYNC_CRITICAL budget.

---

## 2. Top 10 hottest EventBus handlers (by avg ms)

| Rank | Topic | avg_ms | max_ms | n |
|---:|---|---:|---:|---:|
| 1 | `settings.snapshot` | 7.50 | 82.23 | 11 |
| 2 | `capability.providers.ready` | 0.59 | 1.33 | 3 |
| 3 | `orchestration.provider.health` | 0.11 | 0.21 | 20 |
| 4 | `settings.changed` | 0.09 | 0.09 | 1 |
| 5 | `ui.command` | 0.08 | 0.66 | 24 |
| 6 | `chat.history_loaded` | 0.07 | 0.07 | 1 |
| 7 | `capability.lifecycle.snapshot` | 0.06 | 0.14 | 23 |
| 8 | `kernel.state_changed` | 0.06 | 0.06 | 2 |
| 9 | `plugin.catalog` | 0.05 | 0.05 | 1 |
| 10 | `chat.chunk` | 0.05 | 0.13 | 100 |

**By count (volume):** `chat.chunk` (100), `service.state_changed` (82), `service.ready` (82), `system.snapshot` (42), `service.started` (41).

---

## 3. Top 10 AppState notification / reduce sources

Headless `AppStateStore` listener count = **0** (no UI shell). Counts below are **reducer invocations** (`appstate.topic.*`), not UI notifies.

| Rank | Topic | Reduce count |
|---:|---|---:|
| 1 | `chat.chunk` | 100 |
| 2 | `service.state_changed` | 82 |
| 3 | `system.snapshot` | 42 |
| 4 | `service.started` | 41 |
| 5 | `service.ready` | 41 |
| 6 | `capability.lifecycle.snapshot` | 12 |
| 7 | `orchestration.provider.health` | 10 |
| 8 | `execution.authority.decision` | 8 |
| 9 | `action.registered` | 3 |
| 10 | `app.phase` | 2 |

**Structural:** 78 reducers total; `system.snapshot` indexed to **1** reducer; 116 AppState topics in catalog.

**Gap:** Listener notify rate (notifies/s with UI attached) is **not yet instrumented** as a first-class counter. Phase 2 should add `appstate.notify` timing + count before claiming storm targets (e.g. PERF-001 baseline 140 → &lt;25 notifies/s).

---

## 4. UI thread utilization

**Not measurable** on this host. Release gate requires Windows ARM64 + Performance Inspector (`Ctrl+Shift+P`) with `freeze_fix=v5`.

---

## 5. Navigation timings

| Metric | Value |
|---|---|
| Headless `UI_NAVIGATE` publish ×30 total | 0.32 ms |
| Headless mean / max publish | 0.011 / 0.063 ms |
| Tk `_show_view` / pack_forget / sidebar configure | **N/A** — requires GUI |

RCA residual: `_show_view` full pack + 26 sidebar configures remains structural cost on Win ARM64.

---

## 6. Inspector refresh timings

**N/A headless.** Code path: fingerprint coalesce in orchestration/runtime inspectors (post-#110). GUI before/after still required for PERF-002.

---

## 7. SQLite read/write latency

| Metric | Value |
|---|---|
| `journal_mode` | **wal** |
| `synchronous` | 2 (NORMAL) |
| `SELECT 1` mean / max | 0.030 / 0.128 ms |
| Insert+commit mean / max | 1.73 / 7.66 ms |
| `sqlite.telemetry_batch` avg / max | 4.95 / 9.40 ms (n=2) |

Telemetry insert path is batched async (`sqlite.telemetry_batch`). Shared per-connection lock contention under multi-worker load remains a structural risk (PERF register).

---

## 8. Queue depths

| Queue | Depth | Notes |
|---|---:|---|
| EventBus `_dispatch_queue` | 0 | Present; async dispatch **defaults OFF** |
| Constitution budget | &lt;100 | Met in this run |

---

## 9. Soak test summary

| Test | Result |
|---|---|
| `tests/test_perf_architecture.py` (+ reducer perf) | **17 passed** (~56 s) |
| `tests/test_memory_soak.py` (`AICC_SOAK_SECONDS=6`) | **1 passed** (~11 s); RSS growth within threshold |
| Long Win ARM64 UI soak | **Not run** (release gate) |

---

## 10. Known freezes mapped to RCA

Crosswalk from [`PERFORMANCE_RCA_UI_FREEZE_2026-07-24.md`](PERFORMANCE_RCA_UI_FREEZE_2026-07-24.md) and post-fix evidence (`freeze_fix=v5`, #110):

| RCA rank | Issue | Severity | Status @ 5cef96b | Baseline note |
|---:|---|---|---|---|
| 1 | Stale runtime (pre-#106/#107/#108) | S0 | Operational | Verify `freeze_fix=v5` on deploy |
| 2 | `UI_NAVIGATE` feedback loop | S0 | Mitigated | Storm **warnings** still fire under burst |
| 3 | Cross-thread `event_generate` | S0 | Mitigated | UIQueue poll path |
| 4 | `settings.snapshot` heavy handlers | S1 | Partially mitigated (single snapshot) | **Still exceeds 5 ms** (82 ms OpenAI handler) |
| 5 | `UI_COMMAND` SYNC_CRITICAL | S1 | Live design | Headless light (0.25 ms); out of first-pass SYNC set changes |
| 6–9 | AppState / dual projection / snapshot floor | S2 | Partially mitigated (index, metrics-only skip) | **First investigation (PERF-001)** |
| 10 | Inspector full rebuilds | S2 | Fingerprint coalesce | **PERF-002** |
| 11 | Telemetry sync SQLite | S2 | Async batch landed | Monitor contention |
| 12 | Chat stream dual publish | S2 | Live | Volume leader in this run |
| 13 | Navigation `_show_view` cost | S2 | Live | GUI-only measure |
| 15 | SQLite DELETE journal | S3 | **WAL landed** | Closed as journal-mode debt |

---

## Debt seeds (for Performance Debt Register)

| ID | Issue | Severity | Baseline (this report) | Target |
|---|---|---|---|---|
| PERF-001 | AppState notification storms | S1/S2 | High-frequency reduce sources: chat.chunk, service.*, system.snapshot; UI notify rate **unmeasured** | Instrument then &lt;25 UI notifies/s under soak |
| PERF-002 | Inspector rebuilds | S2 | N/A headless | &lt;5 ms refresh |
| PERF-003 | `settings.snapshot` handler over budget | S1 | max **82 ms** (`OpenAIHttpService`) | &lt;5 ms sync budget |
| PERF-004 | Navigation Tk `_show_view` cost | S2 | N/A headless | &lt;16 ms view switch |
| PERF-005 | SQLite lock contention under workers | S2/S3 | write max 7.7 ms microbench; shared lock | No UI-thread wait; async telemetry retained |

---

## Implications for Program 1 sequence

1. Constitution + ADR-007 (docs) — next.
2. Phase 2 instrumentation — especially `appstate.notify` count/timing with UI attached — required before claiming PERF-001 closed.
3. Phase 3 — fix **one** bottleneck after Investigation Report approval.

**Architecture stance:** Assume current architecture is correct until evidence proves otherwise. Prefer repair over replacement.
