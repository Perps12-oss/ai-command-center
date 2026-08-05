# PERF-003 Sequencing Gate

| Field | Value |
|---|---|
| **Date** | 2026-08-04 |
| **Authority** | Tom audit rev 2 (sequencing risk) + this remediation PR |
| **PERF-003 status** | **Not started** in this PR |

## Gate

Do **not** begin PERF-003 (`settings.snapshot` / OpenAI sync handler) until:

1. Tom S1 PerfInspector skip-path fix is on `main` (this PR), **or**
2. PERF-003 lands only as a tightly coupled patch train **with** that S1 fix —
   never independently first.

## When PERF-003 investigation opens

The PERF-003 investigation report **must** state explicitly:

- PERF-001 and PERF-002 Art XV remain **Mitigated**, not Closed.
- Win ARM64 soak and before/after GUI timings (Tom D1/D2) are still
  **operator-owned** and open.
- A green PERF-003 PR is **not** a proxy closeout for PERF-001/002.

## This PR

Items covered: S1/D3, D5, D6, D7 only. PERF-003 work is deferred.
