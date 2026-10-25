# EventBus Stage 1 — Performance Investigation Report

**Date:** 2026-08-16  
**Stream:** D  
**Authority:** [`IP_D_EVENTBUS_ISOLATION.md`](../architecture/proposals/IP_D_EVENTBUS_ISOLATION.md) §11; [`PERFORMANCE_CONSTITUTION.md`](../../PERFORMANCE_CONSTITUTION.md) Art. IV–V  
**Harness:** `tools/eventbus_stage1_contention.py`, `tests/test_eventbus_stage1_contention.py`  
**Host:** Linux x86_64 Cloud (headless). **`gui_claims_valid: false`.**

## Verdict

**Do not unlock Stream D Stage 2 isolation. Do not draft ADR-026. Do not reopen Gate 2 for pools.**

R4b single-queue FIFO remains authoritative. The abandoned branch `cursor/phase5-async-eventbus-744e` remains **not a merge candidate**.

SYNC_CRITICAL work (`UI_COMMAND`) stays **inline** and well under the 5 ms handler budget while a slow ASYNC worker backlog exists. That is the starvation hypothesis IP-D required us to test. It did not hold on this host.

## Budgets vs measurement

| Metric | Budget | Observed (headless) | Result |
|--------|--------|---------------------|--------|
| Publish (baseline avg / p99) | &lt;0.2 ms | 0.011 / 0.014 ms | Met |
| SYNC_CRITICAL complete p99 (slow-async interference) | &lt;5 ms | 0.020 ms | Met — **not starved** |
| SYNC_CRITICAL complete p99 (Gate 4 topic mix) | &lt;5 ms | 0.008 ms | Met |
| Queue depth | &lt;100 | Peak **1532** on 2000-event fast burst; peak **200** with 200 slow async jobs | Burst backlog on unbounded queue (default `EVENTBUS_QUEUE_MAX_DEPTH=0`) |
| Drops | telemetry-only policy | 0 | Met |
| FIFO (CHAT_CHUNK seq) | preserve | true | Met |

## Interpretation

Instantaneous queue depth above 100 during a synthetic burst is **catch-up on a single worker**, not publisher blocking and not UI/critical delay. Default depth is unbounded, so the PERF queue-depth number is a design target, not an enforced cap. Isolation pools would not change SYNC_CRITICAL latency here because those topics already bypass the queue.

Gate 4 topics (`decision.record.updated`, `autonomy.score.updated`, `model.selected`, `federation.query.request`) mixed with `UI_COMMAND` did not invert priority on this harness.

## What this report cannot close

PERFORMANCE_CONSTITUTION Art. V: Linux headless CI **does not** substitute for Windows ARM64 GUI budgets (UI thread &lt;2 ms avg / P99 &lt;8 ms, navigation &lt;16 ms). Operator-owned soak remains required before any GUI performance close-out. That soak is **not** an isolation ADR.

## Unlock condition (unchanged)

Reopen Gate 2 for isolation **only if** a later report shows, on the appropriate host:

1. SYNC_CRITICAL / UI-path p99 over 5 ms **because** of async-queue interference (not because a SYNC handler itself is slow), or  
2. Sustained (not instantaneous burst) queue depth / drops that violate backpressure policy under realistic A–C–E emission, or  
3. Windows ARM64 GUI evidence of UI starvation attributable to the single dispatch worker.

Until then: Stage 1 is **complete as measurement**; Stage 2 stays **blocked**.

## Reproduction

```bash
PYTHONPATH=. python3 tools/eventbus_stage1_contention.py
APPDATA=/tmp/aicc_appdata python3 -m pytest tests/test_eventbus_stage1_contention.py --no-cov
```
