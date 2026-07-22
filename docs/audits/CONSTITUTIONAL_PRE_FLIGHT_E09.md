# Constitutional Pre-Flight — PR-UI-E09 Agent Operations Center

**Slice:** PR-UI-E09 — Agent Operations Center  
**Baseline:** `origin/main` @ `d2d8dca` (post-E08 #98)  
**Builder:** Cursor (sole coder + Tom auditor)

---

## Authority checks

- [x] Constitution / UI Constitution Art. 14 (Agent Monitor) + Art. 21
- [x] ADR-006 — no OperatorKernel; cancel remains `AGENT_CANCEL_REQUEST`
- [x] Reuse `TimelineRenderer` for run timeline (no parallel timeline engine)
- [x] Evolve existing `AgentsView` / `agent_monitor` panels — do not delete
- [x] Roadmap E09

---

## Scope

1. Add `ui/components/agent/` — `agent_card`, `pipeline_stage`, `run_timeline`
2. Evolve `AgentsView` to compose ops strip (cards + stage + timeline) over Phase 11D panels
3. Add `UI_AGENT_*` topics + controller publish helpers
4. Enrich inspect payload for selected run
5. Tests under `tests/ui/views/test_agent_operations_view.py`

No E10–E13 in this PR. No new AppState fields.

---

## AppState

- Fields added: **none** — project `agent_pipeline`

---

## Pre-flight verdict

**GO**
