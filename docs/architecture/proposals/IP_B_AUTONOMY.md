# IP-B — Autonomy (ADR-022 remainder)

**Status:** GATE 1 DRAFT — awaiting owner Gate 2  
**Stream:** B  
**Parent ADR:** [ADR-022](../adr/ADR-022_CONFIDENCE_AND_AUTONOMY.md) **Accepted** (composite confidence, not logprobs).  
**Baseline:** [STRATEGIC_GAP_MATRIX.md](../../audits/STRATEGIC_GAP_MATRIX.md) Stream B

---

1. **Problem.** ACC must decide auto-execute vs escalate **deterministically**, as policy/runtime, not a threshold invented in a PR. Escalation is the key capability.

2. **Exists.** SecurityTier READ/WRITE/WRITE_DESTROY; BrainRuntime HITL + timeout deny; `PlanStep.require_approval`; PermissionService; `AutonomyScore` with default 0.6; score published on two escalate paths with heuristic component values; **score does not authorize execution**.

3. **Owning boundary.** Policy evaluation in orchestrator / BrainRuntime **before** ExecutionAuthority proceeds. Autonomy is a **permit/escalate classifier**, not an intake.

4. **Remain authoritative.** ExecutionAuthority (ADR-006), receipts, scheduler, TruthBoundary, WRITE_DESTROY always HITL. Direct goal/scheduler bypasses remain forbidden.

5. **New behavior.** Compute composite score from real signals (policy, WM/evidence, verification, recent receipts). Escalate when aggregate below owner-set threshold **or** policy demands HITL. Map bands (proposed for Gate 2, **not** implementer-invented): LOW → auto (still sandboxed); MEDIUM → constrained / extra validation; HIGH → owner approval. Denial, timeout, overrides, audit trail. Ordinary-path scoring with Stream A records.

6. **Rejected.** Logprob-primary autonomy (ADR-022 A); high confidence overriding WRITE_DESTROY; a second `execute()` path; magic numbers in service code without settings/ADR.

7. **Dependencies.** ADR-004, ADR-021, ADR-019 stuck/replan, Stream A emission.

8. **Invariants.** Inv 3 EventBus; no service→service calls; Inv 12 no shims around EA; Art. IX.

9. **Tests.** Deterministic thresholds; escalate/deny/timeout; policy override; audit; receipts; **attempted bypass of EA fails**; WRITE_DESTROY never auto.

10. **Invalid if.** AutonomyService (or equivalent) publishes `tool.invoke` / run requests itself; score overrides hard policy; thresholds only in comments; no audit.

**Gate 2 ask:** ACCEPT numeric bands + whether `< threshold` **blocks** vs **requests approval**; record in ADR-022 addendum. Do not implement until those numbers exist.
