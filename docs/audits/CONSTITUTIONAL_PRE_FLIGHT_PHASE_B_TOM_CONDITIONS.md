# Constitutional Pre-Flight — Phase B Tom Conditions Remediation

**Slice:** Phase B package CONDITIONS (E07 inspect + E02 context goal + debt)  
**Baseline:** `origin/main` @ `8f5c9b8` (post-E13 #103)  
**Builder:** Cursor (sole coder + Tom auditor)

---

## Authority checks

- [x] Package Tom audit `TOM_AUDIT_PHASE_B_UI_PACKAGE_E00_E13.md`
- [x] UI Constitution / AppState boundaries
- [x] No new graph/timeline/inspector engine

---

## Scope

1. E07 — publish inspect kind `task` (not `plan_step`); map + tests
2. E02 — GlobalContextBar shows active goal from `brain_state` (+ snapshot fields)
3. Wire `UI_MEMORY_SEARCH` from MemoryView search
4. Remove leftover `chat/inspector/__pycache__`
5. Backfill Tom audits E00–E03; refresh Implementation Truth Matrix Phase B rows
6. Include package audit artifact; re-audit CONDITIONS cleared

Debt included: extract ActionCard to `quick_action_card.py` (HomeView may remain unused shell). Full HomeView deletion still deferred.

---

## AppState

- `GlobalContextSnapshot`: add `active_goal_id`, `active_goal_title` (projected; bar also reads `brain_state` for live goal)

---

## Pre-flight verdict

**GO**
