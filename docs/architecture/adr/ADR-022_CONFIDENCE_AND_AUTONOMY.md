# ADR-022: Confidence & Autonomy

**Status:** Accepted — Composite confidence (Evidence / Verification / Policy / Execution)  
**Date:** 2026-08-05  
**Deciders:** Multi-council Architecture Decision Framework  
**Related:** ADR-004, ADR-018, ADR-021, PermissionService, SecurityTier  
**Framework:** `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`  
**Baseline:** `origin/main` @ `631b1f3`

---

## 1. Problem Statement

How should ACC decide when to act **autonomously** vs escalate to a human?

A common proposal uses token log-probabilities of tool-name tokens as confidence, with thresholds (e.g. &lt;0.60 escalate). ACC already has SecurityTiers, `require_approval`, and PermissionService. Logprob-primary autonomy is poorly calibrated on local models and incomparable across providers.

---

## 2. Current Repository

| Fact | Evidence |
|------|----------|
| SecurityTier | READ / WRITE / WRITE_DESTROY — [`runtime_safety.py`](../../../ai_command_center/domain/runtime_safety.py) |
| BrainRuntime approval | WRITE_DESTROY always needs approval; 60s timeout denies — [`brain_runtime_service.py`](../../../ai_command_center/services/brain_runtime_service.py) |
| PlanStep.require_approval | Orchestrator pauses for approval |
| PermissionService | Actor defaults (user vs agent); interactive checks — [`permission_service.py`](../../../ai_command_center/core/permission/permission_service.py) |
| RetryHint | Typed hints; no auto-retry for WRITE/DESTROY per ADR-004 |
| logprob | **Zero** matches in repository |
| “Confidence” fields | Heuristic / observation averages / planner JSON gate — not token logprobs |

**Status:** Policy-based autonomy. No statistical logprob gate.

---

## 3. Independent Review Proposal

After grammar-constrained (or free) tool generation, average log-probabilities of tool-name (and critical arg) tokens; convert to confidence. Policy: &gt;0.85 auto-execute (still respect sandbox/tiers); 0.60–0.85 execute with post-hoc flag; &lt;0.60 pause and escalate with alternatives. Use this as the primary uncertainty→HITL bridge.

---

## 4. Architect Council

**Defense of Proposal A (logprob confidence):**

- Models are often implicitly uncertain while forced to emit one sample; logprobs recover discarded signal.
- Continuous score is finer than binary `require_approval` flags.
- Bridges safety infrastructure and reasoning quality for small local models.
- Beam/top alternatives can be shown to users when confidence is low.
- Industry inference APIs increasingly expose logprobs.

---

## 5. Red Team

| Axis | Attack |
|------|--------|
| Assumptions | Confidence ≠ correctness; high logprob wrong actions still happen. |
| Scalability | Ollama path may not expose comparable logprobs; OpenAI vs local incomparable. |
| Uniqueness | Generic agent uncertainty UX. |
| Maintainability | Thresholds become magic numbers per model; recalibrate on every model swap. |
| Production | False auto-approve when model is confidently wrong; false escalate storms when under-calibrated. |
| Architecture | Couples autonomy to inference vendor features (conflicts ADR-023 brain independence). |

---

## 6. Alternative Architecture Team

**First principle:** Autonomy is a **composite of grounded signals**, not token heat.

```text
AutonomyScore =
  PolicyConfidence      (SecurityTier, require_approval, PermissionService)
  × EvidenceConfidence  (WM facts / observations present and consistent)
  × VerificationConfidence (TruthBoundary / success criteria)
  × ExecutionConfidence (recent receipt success, stuck/replan history)
```

- Escalate when composite below threshold **or** when policy demands HITL (WRITE_DESTROY always).
- Logprobs may be optional telemetry later — never the primary autonomy authority.
- Aligns with Decision Records (ADR-021).

---

## 7. Systems Review Board

| Criteria | A Logprob primary | B Composite |
|----------|-------------------|-------------|
| Simplicity | 4 | 3 |
| Performance | 4 | 4 |
| Reliability | 2 | 5 |
| Local LLM | 1 | 5 |
| Testability | 2 | 5 |
| Extensibility | 3 | 5 |
| Uniqueness (Workspace OS) | 2 | 5 |
| Production Risk | 5 | 2 |

---

## 8. Constitution Guardian

| Question | Finding |
|----------|---------|
| More like every other assistant? | **A: Yes.** |
| Erode Workspace OS? | Mild for A; B strengthens policy/evidence culture. |
| Debt? | A embeds vendor logprob APIs into autonomy core. |
| Inv 13? | **A conflicts** if cloud logprobs required for safe autonomy. |
| Temporary as permanent? | Threshold tuning becomes permanent safety theater. |

Guardian **rejects A as primary**; composite may include optional debug signals later.

---

## 9. Council Decision

**Accept B.**

1. Autonomy uses **composite** Evidence / Verification / Policy / Execution confidence.
2. Policy gates (SecurityTier, `require_approval`, permissions) remain hard constraints — not overridden by high “confidence.”
3. Do **not** depend on provider logprobs for autonomy decisions.
4. WRITE_DESTROY remains HITL regardless of composite score.

---

## 10. Actionable Implementation Plan

| Milestone | Work | Tests / verification |
|-----------|------|----------------------|
| M1 | Define `AutonomyScore` domain dataclass with four components + aggregate | Unit tests |
| M2 | Compute score at orchestrator / BrainRuntime gate points from existing signals | Service tests |
| M3 | Escalate to approval when aggregate &lt; configurable threshold; never bypass WRITE_DESTROY | Integration tests |
| M4 | Project score into Decision Record / Approvals UI | AppState / UI projection tests |
| Out of scope | Logprob-primary thresholds; beam-search UI as autonomy core | — |

**Dependencies:** ADR-004 tiers, ADR-021 Decision Record, ADR-019 stuck/replan signals.  
**Migration:** Additive; existing approval paths remain.

---

## References

- `docs/architecture/adr/ADR-004_RUNTIME_APPROVAL_MODEL.md`
- `docs/architecture/RUNTIME_SAFETY.md`
- `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`
