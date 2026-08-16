# Constitutional Pre-Flight — Gate 4 Streams A, B, C, E, B5

**Date:** 2026-08-16  
**Task:** Gate 4 product code against merged Gate 3 plans (ADR-021 §12, ADR-022 §12, ADR-023 §12, ADR-024 §9, ADR-006 §12).  
**Status:** APPROVED

## Task Description

Implement the **ADR plans**, not the informal topic/file inventions in the delegation brief.

| Stream | Follow | Do **not** invent |
|--------|--------|-------------------|
| A | `decision.record.updated`; orchestrator ordinary-path emit; `__missing__`; execution-event history; UI projection; TruthBoundary join; DecisionCard only when pending | `DECISION_RECORD_CREATED` / `DECISION_RECORD_AUDIT_ENTRY`; `core/decision_record.py` |
| B | §11 bands; escalate-only; `autonomy.score.updated` + `band`; real component scores; no EA bypass | `CONFIDENCE_ESCALATION_REQUIRED`; `core/confidence_model.py`; MEDIUM = “escalate if high-impact” |
| C | Sequential ADR M2 (per-tier map, already largely live) → M3 local-only replan/destroy → M4 telemetry reason, never gates authority | Fallback-as-architecture, tier pooling, complexity orchestration (capability-registry extras / future IP) |
| E | Factory-wire existing FederationService; existing federation.* topics; provenance; no embeddings | `FEDERATION_QUERY` / `FEDERATION_RESULTS` new topics |
| B5 | Verify #168 path; add `-k goal_intake_hero` coverage | Re-route Hero (already done) |

## Authorities Reviewed

- `PROJECT_CONSTITUTION_V4.md` (Inv 1, 2, 6, 9, 11, 13; Art. VII, X)
- `AGENTS.md` / `docs/ARCHITECTURE_ENFORCEMENT.md` (Gate 4 = code against Gate 3 only)
- ADR-006 §12, ADR-021 §12, ADR-022 §12, ADR-023 §12, ADR-024 §9
- `WAVE_1_GATE_2_DECISIONS.md`

## Files Reviewed

Orchestrator, DecisionRecord, AutonomyScore, ExecutionEventService, FederationService, service_factory, ModelRouterService, test_b5_hero_ea_intake, test_model_tier_map, brain_panel, approvals_view DecisionCard.

## Protected Assets Impacted

ExecutionOrchestrator (receipts/TruthBoundary must not weaken). ExecutionAuthority intake unchanged. UCGS `scope_embeddings` stays S5.

## Sources of Truth Impacted

None new. Decision Records and federation queries are derived views. Receipts/WM remain SoT.

## Architectural Invariants Impacted

Inv 2 (UI renderer), Inv 6 (no second ContextManager), Inv 9 (telemetry observes), Inv 11 (no index SoT), Inv 13 (no vendor Brain branches).

## Contracts Impacted

Existing topics only. Optional payload keys: `band` on autonomy score; `provenance` on federated nodes; `__missing__` in DecisionRecord fields.

## Gate Impact Assessment

Gate 4 for named streams. D isolation, E vectors, F Adapt, G still blocked. C M2 tests already on `main`; M3/M4 may follow in this change set.

## Historical Gate Impact

Do not regress #161 TruthBoundary facts or #168 Hero EA intake.

## Regression Risk

Orchestrator extra publishes on every step — keep bounded. Autonomy band change must not fail existing 0.9/0.2 domain tests. Federation factory adds one READY service.

## Constitutional Status

APPROVED
