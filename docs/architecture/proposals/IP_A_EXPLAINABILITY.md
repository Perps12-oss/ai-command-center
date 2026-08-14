# IP-A — Explainability (ADR-021 remainder)

**Status:** GATE 2 CLOSED 2026-08-14 — ACCEPT full M2–M5. Decision: [`ADR-021` §11](../adr/ADR-021_EXPLAINABILITY.md#11-gate-2-addendum--wave-1-closure-2026-08-14).  
**Stream:** A  
**Parent ADR:** [ADR-021](../adr/ADR-021_EXPLAINABILITY.md) **Accepted** (Decision Record architecture). This proposal does **not** reopen CoT-as-SoT.  
**Baseline:** [STRATEGIC_GAP_MATRIX.md](../../audits/STRATEGIC_GAP_MATRIX.md) Stream A

---

1. **Problem.** Users and auditors need “why did it act?” as inspectable **runtime evidence**, not a chat monologue. Remaining gap: Decision Records are not produced for ordinary success/failure, so the trust surface is incomplete.

2. **Exists.** `DecisionRecord`; topics `decision.record.updated`; AppState projection; emit on awaiting-approval and replan-stuck only; TruthBoundary on orchestration verification; receipts/Evidence UI; Brain Inspector state projection.

3. **Owning boundary.** Execution / orchestration services publish records onto EventBus. AppState projects. UI renders. LLM may **compose** a summary field from the record; it must not invent evidence.

4. **Remain authoritative.** ExecutionReceipt, TruthBoundary, World Model observations, SecurityTier/policy, ExecutionAuthority decisions. Scratchpad/CoT never SoT (ADR-021 Council).

5. **New behavior.** Emit DecisionRecord on ordinary step success and failure with populated evidence/policy/receipt/verification (or explicit empty/missing markers). Persist or index enough for historical inspectability. Surface fields in Evidence / Approvals / Mission Control. Optional DecisionCard wiring (ADR-021 M5) only after records are truthful.

6. **Rejected.** Forced `<SCRATCHPAD>` primary UX; generated retrospective prose as audit authority; silent omission of missing evidence.

7. **Dependencies.** Stream B shares `_publish_decision_and_autonomy`. Receipts, ADR-018/019 observations.

8. **Invariants.** Inv 2 (UI renderer); Inv 11 (single SoT — record is a **projection of** receipts/policy, not a rival SoT); Art. VII (no weakening TruthBoundary).

9. **Tests.** Emit on success/failure; record fields subset of actual receipts/WM; contradiction between explanation text and receipt fails; missing evidence encoded; historical lookup; no fabrication.

10. **Invalid if.** Records exist without receipts; LLM text treated as facts; second execution log diverges from EA/orchestrator; CoT streamed as Mission Control authority.

**Gate 2 ask:** ACCEPT remaining Section 9 M2–M5 with ordinary-path emission **or** DEFER WITH CONDITION (name which milestones). REJECT only if owner withdraws Decision Record completeness.
