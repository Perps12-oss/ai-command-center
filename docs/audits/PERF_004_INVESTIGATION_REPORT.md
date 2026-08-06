# PERF-004 Investigation Report — Navigation `_show_view` cost

| Field | Value |
|---|---|
| **Date** | 2026-08-06 |
| **Debt** | PERF-004 (Performance Debt Register) |
| **Status** | Phase 2 + Phase 3 fix |
| **Code tip** | `cursor/perf004-navigation-show-view-30d3` |
| **Method** | Code-path analysis + headless configure/pack contracts (Tk ms N/A headless) |

---

## Sequencing / soak honesty

- PERF-001–003 Art XV remain **Mitigated**, not Closed (operator soak / GUI timings).
- A green PERF-004 PR is **not** a proxy closeout for PERF-001–003.
- View-switch &lt;16 ms on Win ARM64 remains **operator-owned** for Closed.

---

## Constitutional Pre-Flight

| Check | Result |
|---|---|
| Program fence | **Program 1** |
| Ladder | Avoid duplicate configures → delete unnecessary `pack_forget` of non-visible views |
| Out of bounds | PERF-005, SYNC_CRITICAL membership, UI redesign |

---

## Problem

Navigation runs expensive Tk work per view switch (RCA rank 13): full
`pack_forget` of every created view, sidebar badge `configure` ×26 (and twice on
click → `_show_view`), plus state refresh. Target: &lt;16 ms view switch.

## Evidence (tip, pre-fix)

| Work | Every switch? | Notes |
|---|---|---|
| `pack_forget` all created views | Yes | `view_manager.py` `_show_view` |
| `Sidebar._apply_badge_labels` all buttons | Yes | 26× `configure(text=…)` |
| Double `set_active` on click | Yes | `_select` then `_show_view` |
| `NavGroup.set_active` all buttons | **No** | Already dirty prev+new (RCA stale) |
| Same-view `_show_view` from stream/error | Possible | No early-out in `_show_view` |

## Chosen Fix

1. **Avoid:** Dirty badge label updates (prev + new + changed badges only).
2. **Avoid:** `_show_view` skips `set_active` when sidebar already active.
3. **Avoid:** `_show_view` same-view early-out (no pack churn; keep chat focus / settings load side effects).
4. **Delete:** `pack_forget` only the previous view, not every created view.

## Success Criteria

| Criterion | Status |
|---|---|
| `set_active(A→B)` badge configures ≪ 26 | Met (tests) |
| Same-view `_show_view` does not `pack_forget` | Met (tests) |
| Redundant `set_active` skipped | Met (code) |
| Win ARM64 &lt;16 ms | **Operator** |

## Rollback

Revert this PR.
