# PERF-003 Investigation Report — `settings.snapshot` OpenAI handler

| Field | Value |
|---|---|
| **Date** | 2026-08-06 |
| **Debt** | PERF-003 (Performance Debt Register) |
| **Status** | Phase 2 + Phase 3 fix (lazy key resolve) |
| **Code tip** | `cursor/perf003-openai-settings-snapshot-30d3` |
| **Sequencing** | S1 PerfInspector fix on `main` (#154); gate: `PERF_003_SEQUENCING_GATE.md` |

---

## Sequencing gate (mandatory)

- PERF-001 and PERF-002 Art XV remain **Mitigated**, not Closed.
- Win ARM64 soak and before/after GUI timings (Tom D1/D2) are still
  **operator-owned** and open.
- A green PERF-003 PR is **not** a proxy closeout for PERF-001/002.

---

## Constitutional Pre-Flight

| Check | Result |
|---|---|
| Program fence | **Program 1** only |
| Ladder | Delete keyring from SYNC_CRITICAL path → lazy resolve on auth |
| Out of bounds | SYNC_CRITICAL membership, EventBus async defaults, PERF-004 |

---

## Problem

`OpenAIHttpService._on_settings_snapshot` exceeded the 5 ms SYNC_CRITICAL budget
(baseline max **82.23 ms**). Theme/settings writes stalled the publish thread.

## Evidence

| Source | Finding |
|---|---|
| Baseline | `settings.snapshot` avg 7.50 / max 82.23 ms (`OpenAIHttpService`) |
| Call chain | `SettingsService.set` → `SETTINGS_SNAPSHOT` → `_on_settings_snapshot` → `resolve_openai_api_key` → `keyring.get_password` |
| Root cause | Cold keyring I/O on the sync bus handler |

Double-publish of `settings.snapshot` per `set`: **already fixed** (one snapshot).

## Chosen Fix

**Delete** `resolve_openai_api_key` from `_on_settings_snapshot`. Store opaque
`openai_api_key` settings value only. **Avoid** by resolving lazily in
`_resolved_api_key()` / `_auth_headers()` / health / stream (secret_store cache
still applies).

## Success Criteria

| Criterion | Status |
|---|---|
| Handler does not call `resolve_openai_api_key` | Met (test) |
| Snapshot apply &lt;5 ms headless (no keyring) | Met (test) |
| Auth still resolves on demand | Met (lazy path) |
| Art XV Closed | **No** — Mitigated; Win soak operator |

## Rollback

Revert this PR. No env flag.
