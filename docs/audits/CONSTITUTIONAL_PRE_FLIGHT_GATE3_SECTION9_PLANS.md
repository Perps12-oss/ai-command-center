# Constitutional Pre-Flight — Gate 3 Section 9 plans (Streams A, B, C, E)

**Date:** 2026-08-16  
**Task:** Add Gate 3 implementation plans (program “Section 9 plan”: files, interfaces, migrations, tests, wiring, docs, acceptance, rollback) for ADR-021 M2–M5, ADR-022 bands/escalation, ADR-023 sequential M2→M4, ADR-024 M1 read-only federation. Docs only. No Gate 4 code.  
**Status:** APPROVED

## Task Description

Wave 1 Gate 2 is on `main`. Each Accepted/deferred stream’s §11 (or ADR-024 §8) names Gate 3 as the next step. This change writes those plans into the ADRs. Existing §9 Council Decision text on ADR-021–023 is **not** rewritten (that section is the architecture decision, not the implementation plan). Gate 3 content is added as **§12** on 021–023 and as **§9** on ADR-024 (which has no council §9).

## Authorities Reviewed

- `PROJECT_CONSTITUTION_V4.md` (Inv 2, 6, 9, 11, 13; Art. VII, X)
- `AGENTS.md` / `docs/ARCHITECTURE_ENFORCEMENT.md`
- `docs/governance/STRATEGIC_RUNTIME_PROGRAM.md` (Gate 3 required outcome)
- `docs/architecture/proposals/WAVE_1_GATE_2_DECISIONS.md`
- ADR-018 §10 (format/depth for an actionable plan)
- ADR-021 §9–11, ADR-022 §9–11, ADR-023 §9–11, ADR-024
- `docs/audits/STRATEGIC_GAP_MATRIX.md`

## Files Reviewed

- `ai_command_center/domain/decision_record.py`
- `ai_command_center/domain/autonomy_score.py`
- `ai_command_center/services/execution_orchestrator_service.py` (`_publish_decision_and_autonomy`)
- `ai_command_center/services/federation_service.py`
- `ai_command_center/core/service_factory.py` (no FederationService today)
- `ai_command_center/services/model_router_service.py`
- `ai_command_center/orchestration/verification/truth_boundary.py`

## Protected Assets Impacted

None in this PR. Gate 4 PRs that follow these plans will touch ExecutionAuthority/orchestrator, AppState, and (E) factory wiring — those PRs need their own pre-flights.

## Sources of Truth Impacted

Plans require: receipts/WM remain SoT for Decision Records; AutonomyScore never a second execute path; model_tier_map stays settings; federation is a read-only view. No SoT change in this docs PR.

## Architectural Invariants Impacted

- Inv 2, 9, 11, 13 as already decided in Wave 1. Plans must not reopen CoT-as-SoT, EA bypass, embeddings, or vendor-hardcoded Brain branches.

## Contracts Impacted

Existing topics: `decision.record.updated`, `autonomy.score.updated`, `federation.query.*`. No new canonical topics invented here except optional `decision.record.missing` **marker inside payload**, not a new bus topic.

## Gate Impact Assessment

This **is** Gate 3. It unblocks Gate 4 only for the named milestones. Stream D, Stream E vectors, Stream F Adapt rows, Stream G remain blocked per Wave 1.

## Historical Gate Impact

Does not declare Wave 2 complete. Phase-complete-on-main still applies to later implementation.

## Regression Risk

Docs only.

## Constitutional Status

APPROVED
