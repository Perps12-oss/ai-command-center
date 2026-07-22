# Constitutional Pre-Flight — PR-UI-E10 Evidence Workspace

**Slice:** PR-UI-E10 — Evidence Workspace  
**Baseline:** `origin/main` @ `2a2c3c9` (post-E09 #99)  
**Builder:** Cursor (sole coder + Tom auditor)

---

## Authority checks

- [x] Constitution / UI Constitution Art. 13 (Execution Center truth/receipt) + Art. 21
- [x] ADR-006 — project `orchestration_run` only; no second SoT
- [x] Reuse receipt/truth helpers from Execution Center panels
- [x] New EvidenceView registered beside executions (Ops)
- [x] Roadmap E10

---

## Scope

1. Add `ui/components/evidence/` — claim_card, truth_badge, receipt_chain
2. Add `EvidenceView` list + detail (facts, receipt, trace)
3. Register `evidence` in VIEW_IDS / sidebar / state_applier / palette
4. Add `UI_EVIDENCE_*` topics + controller + inspect wiring
5. Tests under `tests/ui/views/test_evidence_view.py`

No new AppState fields — reuse `orchestration_run`. No E11–E13.

---

## AppState

- Fields added: **none** — project `orchestration_run`

---

## Pre-flight verdict

**GO**
