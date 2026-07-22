# Constitutional Pre-Flight — PR-UI-E11 Mission Control Operations

**Slice:** PR-UI-E11 — Mission Control Operations  
**Baseline:** `origin/main` @ `e5c821d` (post-E10 #100)  
**Builder:** Cursor (sole coder + Tom auditor)

---

## Authority checks

- [x] Constitution / UI Constitution Art. 13–14 + Art. 21
- [x] ADR-006 — reuse ExecutionTimelineDock / TimelineRenderer (no new timeline engine)
- [x] Project existing AppState (`operation_library_index`, `operation_journal`, `execution_scrubber`, `agent_pipeline`) — no new fields
- [x] Roadmap E11

---

## Scope

1. Add `ui/components/operations/` — pipeline_stage, operation_card
2. Add `OperationsView` with stage strip + Operation cards + ExecutionTimelineDock
3. Register `operations` in VIEW_IDS / sidebar / state_applier / palette / command_classify
4. Add `UI_OPERATION_*` topics + scrub → inspect wiring
5. Tests under `tests/ui/views/test_operations_view.py`

No E12–E13. No new AppState reducer.

---

## AppState

- Fields added: **none**

---

## Pre-flight verdict

**GO**
