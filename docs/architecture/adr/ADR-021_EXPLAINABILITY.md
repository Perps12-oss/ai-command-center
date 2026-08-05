# ADR-021: Explainability

**Status:** Accepted — Decision Records (Evidence + Policy + Receipts + Verification)  
**Date:** 2026-08-05  
**Deciders:** Multi-council Architecture Decision Framework  
**Related:** ADR-004, TruthBoundary, Evidence UI, Brain Inspector  
**Framework:** `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`  
**Baseline:** `origin/main` @ `631b1f3`

---

## 1. Problem Statement

What should users **actually see** when asking why the system acted?

A common proposal forces the model to emit `<SCRATCHPAD>` CoT before `<ACTION>`, then streams that text as Mission Control “Thinking…”. ACC already projects Brain state, receipts, and Evidence UI. Choosing scratchpad as primary trust surface risks model-dependent fiction and security leakage.

---

## 2. Current Repository

| Fact | Evidence |
|------|----------|
| Brain Inspector | Wired UI projects kernel/goals/actions/plan — [`brain_view.py`](../../../ai_command_center/ui/views/brain_view.py) |
| Mission Control “Reasoning” | Mode-derived copy, **not** model CoT — [`brain_panel.py`](../../../ai_command_center/ui/mission_control/brain_panel.py) |
| DecisionCard | Exists under chat views; **unwired** to live consumers |
| TruthBoundary | Receipt-grounded validation class; **not** factory-wired; live orchestration uses simplified success flag |
| Receipts | `ExecutionReceipt` / Evidence view / ReceiptViewer — wired |
| Telemetry | TelemetryService persists bus events |
| CoT / scratchpad stream | Absent |

**Status:** Explainability is state + receipts oriented, incomplete wiring. No authoritative CoT.

---

## 3. Independent Review Proposal

Force THINKING mode: model must write reasoning in `<SCRATCHPAD>` then decision in `<ACTION>`. Parse scratchpad in orchestrator; stream to Mission Control as Thinking before action finalizes. Use scratchpad as the primary answer to “Why did it do that?”

---

## 4. Architect Council

**Defense of Proposal A (scratchpad CoT):**

- Latent anchors: forcing justification before action constrains subsequent tool tokens.
- Debuggability: engineers see the model’s intermediate reasoning in real time.
- User trust: opaque plans feel worse than readable “thoughts.”
- Low implementation cost relative to full verification pipelines.
- Aligns with popular agent UX (visible chain-of-thought panels).

---

## 5. Red Team

| Axis | Attack |
|------|--------|
| Assumptions | Assumes scratchpad is ground truth; models can rationalize after sampling or fabricate. |
| Scalability | Verbose CoT burns context; conflicts with ADR-020 derived-view budgets. |
| Uniqueness | Chatbot “show thinking” UX — not Workspace OS evidence culture. |
| Maintainability | Prompt-tag parsing is brittle; model-dependent formatting. |
| Production / security | Scratchpads may leak secrets, paths, or policy bypass rationales into UI/logs. |
| Verification | Cannot prove action correctness from prose; receipts can. |

---

## 6. Alternative Architecture Team

**First principle:** Explainability is a **Decision Record**, not a monologue.

```text
Decision Record
  ├── Evidence     (observations, WM facts, search hits)
  ├── Policy       (SecurityTier, require_approval, permissions)
  ├── Receipts     (ExecutionReceipt / tool outcomes)
  └── Verification (TruthBoundary / success criteria)
```

- Users see what was known, what policy allowed, what ran, and whether claims were grounded.
- Brain Inspector / Mission Control project **system state**, not model diary.
- Optional non-authoritative debug CoT may exist behind a developer flag — never SoT for trust.

---

## 7. Systems Review Board

| Criteria | A Scratchpad primary | B Decision Record |
|----------|----------------------|-------------------|
| Simplicity | 4 | 3 |
| Performance | 3 | 4 |
| Reliability | 2 | 5 |
| Local LLM | 3 | 5 |
| Testability | 2 | 5 |
| Extensibility | 3 | 5 |
| Uniqueness (Workspace OS) | 2 | 5 |
| Production Risk | 4 | 2 |

---

## 8. Constitution Guardian

| Question | Finding |
|----------|---------|
| More like every other assistant? | **A: Yes.** |
| Erode Workspace OS? | **A: Yes** if Evidence/World Model yield to chat thinking panels. |
| Debt? | Prompt-tag protocol becomes permanent UI contract. |
| Inv 2? | UI must not become a business-logic interpreter of freeform model text as authority. |
| Security? | Scratchpad-as-default increases leak surface. |

Guardian **rejects A as primary explainability architecture**.

---

## 9. Council Decision

**Accept B.**

1. Primary user-facing explainability is the **Decision Record**: Evidence + Policy + Receipts + Verification.
2. Mission Control / Brain Inspector continue to project **state**, not model CoT, as authoritative “why.”
3. CoT / scratchpad streaming is **non-authoritative debug only** if ever added; never the trust surface.
4. Follow-on work may wire `TruthBoundary` and `DecisionCard` into live paths consistent with this record.

---

## 10. Actionable Implementation Plan

| Milestone | Work | Tests / verification |
|-----------|------|----------------------|
| M1 | Define `DecisionRecord` domain dataclass + AppState projection + EventBus topic(s) | Unit + AppState tests |
| M2 | Populate record from policy tier, pending approval, receipt, verification status on execution steps | Integration test |
| M3 | Surface Decision Record in Evidence / Approvals / Mission Control (replace “Reasoning” copy with record fields where appropriate) | UI projection tests |
| M4 | Wire TruthBoundary into orchestration path (replace success-only truth_valid where safe) | TruthBoundary tests live |
| M5 | Optionally wire DecisionCard to pending approval intents | UI smoke / unit |
| Out of scope | Forced `<SCRATCHPAD>` as primary UX; CoT as audit authority | — |

**Dependencies:** Receipts, SecurityTiers, ADR-018/019 observation events.  
**Migration:** No removal of Brain Inspector; enrich projections.

---

## References

- `ai_command_center/orchestration/verification/truth_boundary.py`
- `docs/architecture/UI_COMPONENT_SPECS/E06_BRAIN_INSPECTOR.md`
- `docs/architecture/UI_COMPONENT_SPECS/E10_EVIDENCE_WORKSPACE.md`
- `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`
