# PERF-002 S1 Remediation — PerfInspector skip-path (pre-fix note)

| Field | Value |
|---|---|
| **Date** | 2026-08-04 |
| **Debt** | PERF-002 follow-up (Tom audit rev 2: S1 / D3) |
| **Baseline** | `TOM_AUDIT_PERF_001_002_FREEZE_CLOSEOUT_2026-08-04.md` rev 2 |
| **Status** | Fix implemented in PR (S1/D3); Art XV remains Mitigated (D1/D2 open) |

## Problem

PerformanceInspector equality fingerprint includes `uptime_s`. The 1 Hz `_tick`
advances uptime every cycle, so skip never fires and every tick rebuilds the
textbox. AppState fan-out deletion (already on `main`) is out of scope and stays.

## Chosen fix

Exclude `uptime_s` from equality fingerprint. Show live uptime on a cheap label
updated every tick without full textbox rebuild when metrics identity is stable.

## Out of bounds

- D1/D2 Win ARM64 soak / GUI timings (operator)
- Art XV remains **Mitigated** (not Closed)
- PERF-003 not started in this PR
