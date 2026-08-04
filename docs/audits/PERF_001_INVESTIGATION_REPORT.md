# PERF-001 Investigation Report — AppState Notification Storms

| Field | Value |
|---|---|
| **Date** | 2026-08-04 |
| **ADR** | [ADR-007_APPSTATE_NOTIFICATION_STORMS.md](../architecture/adr/ADR-007_APPSTATE_NOTIFICATION_STORMS.md) |
| **Status** | Phase 2 complete · Phase 3 fix landed (`chat.chunk` coalesce) |
| **Code tip** | `cursor/adr007-perf001-appstate-30d3` |
| **Method** | Headless `AppStateStore` + 1 listener (UIController-shaped) |

---

## Problem

High-frequency dirty AppState updates fan out to listeners (UIController,
open inspectors). Even when UI apply is frame-governed, **notify count**
during chat streaming scales with token/chunk rate.

## Evidence (Phase 2 metrics — before coalesce)

Controlled storm (listener attached): 40× `system.snapshot`, 100× `chat.chunk`,
30× `ui.navigate`, 20× `service.state_changed`.

| Metric | Before |
|---|---:|
| Listener notifies | **101** |
| `appstate.notify` | 101 |
| `appstate.notify.topic.chat.chunk` | **100** |
| `appstate.notify.skipped.metrics_only` | 39 |
| Notify avg / max | 0.0005 / 0.0018 ms (empty listener) |
| Implied notify rate | Dominated by chunk rate (≫25/s under live stream) |

**Root cause (confirmed):** `chat.chunk` dirty reduces notify **1:1**. Reduce
cost is cheap; notify *count* is the storm. `system.snapshot` metrics-only skip
already works (39/40 skipped).

## Chosen Fix (Optimization Ladder § coalesce)

Trailing-edge coalesce **listener notify** for `chat.chunk` only (40 ms window,
`APPSTATE_NOTIFY_COALESCE_MS`, `0` = off).

- Reducers still run every chunk (stream buffer complete).
- Non-stream topics remain immediate.
- Flush delivers latest `AppState` once per window.
- Metrics: `appstate.notify.coalesced`, `appstate.notify.flush`.

## Evidence (after)

Same storm with default coalesce:

| Metric | After |
|---|---:|
| Listener notifies (total) | **3** (was 101) |
| `appstate.notify.coalesced` | **100** |
| `appstate.notify.topic.chat.chunk` | **1** (was 100) |
| `appstate.notify.flush` | **1** |
| `appstate.notify.skipped.metrics_only` | 39 (unchanged) |
| Sustained chunk notify ceiling | **≤25/s** (40 ms window) |

## Success criteria

| Criterion | Status |
|---|---|
| Phase 2 `appstate.notify*` metrics exist | Met (pre-existing) |
| Storm reproduced with before numbers | Met |
| Notify rate / listener cost reduced | Met for `chat.chunk` |
| AppState reduce budgets held | Met (unchanged path) |
| Headless tests green | Met (`test_appstate_notify_*`) |
| Win ARM64 soak `freeze_fix=v6` | **Operator** — confirm after merge |

## Out of bounds (unchanged)

- `SYNC_CRITICAL` membership
- `EVENTBUS_DISPATCH_QUEUE` / async adapters defaults
- PERF-002 (see `PERF_002_INVESTIGATION_REPORT.md`) / PERF-003 / PERF-004

## Rollback

`APPSTATE_NOTIFY_COALESCE_MS=0` or revert the AppStateStore coalesce commit.
