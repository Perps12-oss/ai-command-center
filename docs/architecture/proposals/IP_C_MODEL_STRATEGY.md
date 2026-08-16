# IP-C — Model Strategy (ADR-023 remainder)

**Status:** GATE 2 CLOSED 2026-08-14 — ACCEPT sequential M2→M3→M4; capability-registry extras deferred (own future proposal). Decision: [`ADR-023` §11](../adr/ADR-023_MODEL_STRATEGY.md#11-gate-2-addendum--wave-1-closure-2026-08-14).  
**Stream:** C  
**Parent ADR:** [ADR-023](../adr/ADR-023_MODEL_STRATEGY.md) **Accepted** (brain-independent; tiers as settings).  
**Baseline:** [STRATEGIC_GAP_MATRIX.md](../../audits/STRATEGIC_GAP_MATRIX.md) Stream C

---

1. **Problem.** Model use should be **orchestration infrastructure**: task → capability requirements → selection → execution → verification → fallback — not “add more models,” and not vendor IDs in Brain.

2. **Exists.** ModelRouterService (bus-only resolve); `model_tier_map` settings; Ollama/OpenAI adapters; `model.selected`; degrade docs in MODEL_ORCHESTRATION.md; defaults largely undifferentiated local models.

3. **Owning boundary.** ModelRouter + settings + provider adapters. Brain/orchestrator/WM/policy stay model-agnostic. ContextManager remains the only AI context builder (Inv 6).

4. **Remain authoritative.** Runtime contracts, ExecutionAuthority, ARI (externals are capabilities). User-configured cloud IDs allowed in settings; never required in code.

5. **New behavior (sequential M2–M4).** M2: settings maps may differ per tier without vendor branches; context budget may influence **tier hint**, not control flow. M3: replan/destroy work local-only (HITL instead of cloud). M4: telemetry records model/provider/reason; **never** gates authority on cloud availability. Later: capability metadata, health, cost/latency as **settings-backed policy**, fallback owned by router result + degrade mode — not by the model.

6. **Rejected.** Architectural `critical = gpt-4o`; Brain calling vendor SDKs; model choosing tools/routing; shipping all milestones in one pass.

7. **Dependencies.** Provider hardening, SettingsSnapshot, ADR-019 replan (quality optional), Stream A/B for HITL degrade.

8. **Invariants.** Inv 13; ARI; no global CURRENT_MODEL.

9. **Tests.** Distinct tier maps; local-only replan/destroy; provider error → degrade/HITL; telemetry present; authority unchanged when cloud down.

10. **Invalid if.** `if model == "gpt-4o"` in Brain; cloud required for WRITE_DESTROY reasoning; router skipped via direct provider call from UI/services.

**Gate 2 ask:** ACCEPT sequential M2→M3→M4 as remaining Section 9 **or** DEFER specific milestones with conditions. Capability-registry extras need explicit ACCEPT (may be ADR-024 if they change architecture).
