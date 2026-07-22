# Constitutional Pre-Flight — PR-UI-E08 World Model Explorer

**Slice:** PR-UI-E08 — World Model Explorer  
**Baseline:** `origin/main` @ `3fd9b42` (post-E07 #97)  
**Builder:** Cursor (sole coder + Tom auditor)

---

## Authority checks

- [x] Constitution / UI Constitution Art. 12 (World Model) + Art. 21
- [x] ADR-006 — reuse `BaseGraphCanvas`; no second graph engine
- [x] Compose `SelectionInspectorPanel` (retain Art. 12 panel; inspect rail via `world_node`)
- [x] Evolve existing `WorldExplorerView` / Phase 11B panels — do not delete
- [x] Roadmap E08

---

## Scope

1. Add `ui/components/world_model/node_filters.py` — shared filter helpers + filter bar
2. Evolve `WorldExplorerView` — shared filters drive list + graph; inspect select
3. Add `UI_WORLD_*` topics + controller publish helpers
4. Wire dual-publish (UI + domain `WORLD_MODEL_NODE_SELECTED` + inspect)
5. Tests under `tests/ui/views/test_world_explorer_view.py`

No E09–E13 in this PR. No mutable `WorldModelState` in explorer.

---

## AppState

- Fields added: **none** — project existing `world_model` (`selected_node_id` already present)

---

## Pre-flight verdict

**GO**
