# ADR-021: Explainability

**Status:** Accepted — Decision Records (Evidence + Policy + Receipts + Verification)  
**Gate 2 (Stream A remainder):** CLOSED 2026-08-14 — ACCEPT full M2–M5. See §11.  
**Gate 3 (Section 9 plan):** §12 — docs only; Gate 4 code must follow §12 without inventing architecture.  
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

## 11. Gate 2 Addendum — Wave 1 Closure (2026-08-14)

**Proposal:** [`IP_A_EXPLAINABILITY.md`](../proposals/IP_A_EXPLAINABILITY.md)  
**Decision:** **ACCEPT** — full remaining Section 9 scope, M2 through M5. No milestone deferred.

1. Orchestrator emission of `DecisionRecord` extends from the current escalate-only paths (awaiting-approval, replan-stuck) to **every** ordinary execution step, on both **success and failure**.
2. Each emitted record populates real `evidence` / `policy` / `receipt` / `verification` fields from the actual receipt, WM observation, and TruthBoundary result for that step. Where a field genuinely has nothing to report, the record must carry an **explicit missing/empty marker** — never a silently absent key that could be misread as "no evidence exists."
3. Records must be inspectable historically, not only as an AppState latest-only projection. The Section 9 plan (Gate 3) decides the concrete persistence/index shape (e.g. reuse of existing receipt/telemetry storage vs. a dedicated table) — this Gate 2 only mandates that historical lookup is a requirement, not optional.
4. M3's Evidence / Approvals / Mission Control surfacing and M4's `TruthBoundary` wiring proceed as scoped in §10.
5. M5 (`DecisionCard` wiring) remains explicitly conditional: it ships **only after** M2–M4 are verified to produce truthful, non-fabricated records in tests. Do not wire DecisionCard against still-partial data.
6. This addendum does not reopen §9 Council Decision. CoT/scratchpad remains non-authoritative; LLM composition of a record's text is allowed, fabrication of evidence is not (§10 "Out of scope" stands).

**Next step:** Gate 4 implementation against **§12** only. Do not invent architecture in the code PR.

---

## 12. Gate 3 — Section 9 Implementation Plan (M2–M5)

Program Gate 3 (“Section 9 plan”). This does **not** reopen §9 Council Decision. Depth follows ADR-018 §10 plus the required Gate 3 fields (files, interfaces, migrations, tests, wiring, docs, acceptance, rollback).

**Missing-evidence marker (binding):** empty/unknown fields use the string `"__missing__"` as the dict value, or a one-key dict `{"status": "__missing__"}` when a nested object is required. Never omit the key. Never use `{}` to mean “checked and empty of evidence.”

### M2 — Ordinary-path Decision Records

| Field | Plan |
|-------|------|
| **Work** | Call `_publish_decision_and_autonomy` on **every** ordinary step completion (success and failure), not only awaiting-approval (`~389`) and replan-stuck (`~722`). Populate `evidence` / `policy` / `receipt` / `verification` from the step’s receipt, WM observations, SecurityTier/`require_approval`, and `TruthBoundary` result. |
| **Files** | `services/execution_orchestrator_service.py`; `domain/decision_record.py` (optional helper for the marker); `core/app_state.py` (keep latest projection). |
| **Interfaces** | Existing topic `decision.record.updated`. Payload remains `DecisionRecord.to_dict()`. No new execute API. |
| **Migrations** | None for M2 latest-only. Historical inspectability: persist a copy as `ExecutionEvent` with a stable `kind` (e.g. `decision_record`) via `ExecutionEventService` / `ExecutionEventRepository` — **derived log**, receipts remain SoT. No new SoT table. |
| **Wiring** | Orchestrator publishes; AppState already subscribes. EventBus only (no service→service). |
| **Tests** | Emit on success; emit on failure; fields are a subset of actual receipt/WM/policy; contradiction between `summary` and receipt fails the test; omitted keys fail; historical lookup by `run_id`/`step_id` via execution events. Extend `tests/test_decision_autonomy_domain.py` plus orchestrator integration tests. |
| **Docs** | This section; IP-A remains Gate 2 record. |
| **Acceptance** | A successful tool step and a failed tool step each produce a record with real receipt/verification or `"__missing__"`. Escalate-only emission is gone. |
| **Rollback** | Revert orchestrator call sites; leave domain dataclass. |

### M3 — Evidence / Approvals / Mission Control surfaces

| Field | Plan |
|-------|------|
| **Work** | Project Decision Record fields into Evidence workspace, Approvals, and Mission Control “Reasoning” copy. UI reads AppState only. Replace mode-derived Reasoning prose with record fields. |
| **Files** | `ui/views/` Evidence / Approvals / mission_control `brain_panel.py`; AppState `decision_record`. Specs: `E10_EVIDENCE_WORKSPACE.md`, `E06_BRAIN_INSPECTOR.md`. |
| **Interfaces** | No new topics. Renderer binds `decision_record` + historical events already on AppState. |
| **Migrations** | None. |
| **Tests** | UI projection tests: fields shown; `"__missing__"` visible as missing, not as blank success; no CoT/scratchpad as authority. |
| **Acceptance** | Operator can see evidence/policy/receipt/verification for the latest step without opening chat. |
| **Rollback** | Revert UI bindings; records still emit (M2). |

### M4 — TruthBoundary on the live path

| Field | Plan |
|-------|------|
| **Work** | Where orchestration still treats `truth_valid` as success-only, join `TruthBoundary.validate` output into the Decision Record `verification` field. Do not weaken TruthBoundary (Art. VII). Facts must continue `ToolResult.facts` → `TOOL_RESULT` → `step_outputs[].facts` (do not regress #161). |
| **Files** | `orchestration/verification/truth_boundary.py`, `execution_truth.py`, orchestrator. |
| **Tests** | Existing TruthBoundary goldens stay green; new test: failed validation appears on the Decision Record, not only in logs. |
| **Acceptance** | Ungrounded success cannot present as a valid Decision Record. |
| **Rollback** | Keep TruthBoundary live; drop only the record join. |

### M5 — DecisionCard (conditional)

| Field | Plan |
|-------|------|
| **Work** | Wire `ui/views/chat/decision_card.py` to pending-approval intents **only after** M2–M4 tests prove records are non-fabricated. Approvals view already constructs a card (`approvals_view.py`). |
| **Invalid if** | Card ships against empty `{}` receipts. |
| **Tests** | UI smoke/unit: card fields ⊂ Decision Record; no card on ordinary LOW-risk auto-execute unless an approval is actually pending. |
| **Rollback** | Unbind card; leave widget file. |

**Out of scope:** Forced `<SCRATCHPAD>`; CoT as SoT; new explainability SoT besides receipts/WM/policy.

**Dependencies:** Stream B shares `_publish_decision_and_autonomy` — coordinate so M2 here and ADR-022 §12 ordinary-path scoring land without a second publisher.

---

## References

- `ai_command_center/orchestration/verification/truth_boundary.py`
- `docs/architecture/UI_COMPONENT_SPECS/E06_BRAIN_INSPECTOR.md`
- `docs/architecture/UI_COMPONENT_SPECS/E10_EVIDENCE_WORKSPACE.md`
- `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`
- `docs/architecture/proposals/IP_A_EXPLAINABILITY.md`
