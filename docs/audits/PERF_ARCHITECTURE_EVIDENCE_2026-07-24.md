# Performance Architecture — Evidence (2026-07-24)

Branch: `cursor/perf-architecture-freeze-f2e9`  
Fingerprint: `ACC_UI_RUNTIME freeze_fix=v5`

## Behaviour preserved

- Same EventBus topics/payloads
- Telemetry still persisted (async batched worker)
- Settings still publish `settings.changed` + one `settings.snapshot`
- Inspectors show same fields (dirty skip when unchanged)
- Navigation guards from #106–#108 retained

## Changes by phase

| Phase | Implementation |
|---|---|
| 1 EventBus | Publish path unchanged for critical topics; telemetry never SQLite on publish; metrics on handlers |
| 2 AppState | Topic→reducer index + identity dirty detection (no 100-field `__eq__` per event) |
| 3 Inspectors | Fingerprint coalesce + per-textbox dirty content |
| 4 Navigation | Retained reentry/same-view/`after(0)` + bus drop |
| 5 Telemetry | 100% async queue + batch `insert_many` |
| 6 Settings | Single snapshot per logical `set` / `set_many` |
| 7 Streaming | `_try_apply_stream_only` path in StateApplier |
| 8 Keyring | Process cache + invalidate on store |
| 9 SQLite | `PRAGMA journal_mode=WAL` + `synchronous=NORMAL` |
| 10 Observability | Performance Inspector (`Ctrl+Shift+P`) + `PerfMetrics` |

## Headless after-metrics (this environment)

| Metric | After |
|---|---|
| `settings.set` snapshot count | **1** (was 2) |
| AppState SYSTEM_SNAPSHOT reduce | avg **&lt;2ms** (budget in tests) |
| 30× `UI_NAVIGATE` publish | **&lt;60ms** total (no sync SQLite) |
| Reducer index for `system.snapshot` | **&lt; full 78** |

GUI frame times require Windows ARM64; verify with Performance Inspector after deploy (`freeze_fix=v5`).

## Tests

- `tests/test_perf_architecture.py`
- Updated telemetry async tests
