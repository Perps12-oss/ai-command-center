# Constitutional Pre-Flight — PR-UI-E13 Insights Placeholder

**Slice:** PR-UI-E13 — Insights Placeholder  
**Baseline:** `origin/main` @ `9ab5c25` (post-E12 #102)  
**Builder:** Cursor (sole coder + Tom auditor)

---

## Authority checks

- [x] Constitution / UI Constitution Art. 18 (informative empty state)
- [x] Roadmap E13 — stub view + sidebar + topics + `insights_state`
- [x] No second insights engine; placeholder only for Phase 10+
- [x] UI reads AppState / publishes EventBus only

---

## Scope

1. Add `core/state/insights_state.py` — `InsightsSnapshot` + reducer
2. Wire `insights_state` onto `AppState`
3. Add `InsightsView` — Art. 18 Phase 10 placeholder
4. Register `insights` + `UI_INSIGHTS_*`
5. Tests under `tests/ui/views/test_insights_view.py`

No further Phase B evolution slices in this PR.

---

## AppState

- Fields added: `insights_state: InsightsSnapshot`

---

## Pre-flight verdict

**GO**
