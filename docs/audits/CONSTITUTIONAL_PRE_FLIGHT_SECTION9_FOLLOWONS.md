# Constitutional Pre-Flight — Section 9 ADR Follow-ons (018–023)

**Date:** 2026-08-06  
**Branch:** `cursor/section9-adr-followons-621d`  
**Authority:** `PROJECT_CONSTITUTION_V4.md` Art. X; Accepted ADR-018–023

## Scope (this PR)

First implementation slice of Section 9 plans:

| ADR | Milestones in this PR |
|-----|------------------------|
| 018 | M1 intention contract + PlanStep↔Intention; M2 validation before TOOL_INVOKE + parse/validation failure topics; M4 ADR-009 confirmation alignment (`tool.confirmation_*` keyed by run_id:step_id) |
| 019 | M1 execution observation events + BrainRuntime WM apply; M2 replan topics + PlannerService handler; M3 bounded replan on fail; M4 stuck similarity utility + escalate |
| 020 | M1 memory boundary doc; M2 WM-first context builder (workspace snippets outrank chat history) |
| 021 | M1 DecisionRecord domain + AppState projection; TruthBoundary live wire in OrchestrationService; DecisionCard in ApprovalsView |
| 022 | M1 AutonomyScore domain (+ projection) |
| 023 | M1 degrade-mode documentation; M2 distinct tier settings tests |

## Protected assets

- EventBus topics (new canonical topics added under Topic Governance)
- Domain contracts (new dataclasses)

## Sources of truth

- No change to MemoryGraph / WM / Settings SoT ownership
- Observations are EventBus facts for replan; WM apply remains BrainRuntime-owned (orchestrator does not call `worldModel.apply`)

## Invariants

| Invariant | Compliance |
|-----------|------------|
| 1 Ownership | UI unchanged; services publish via EventBus |
| 2 UI isolation | No UI business logic added |
| 3 EventBus | Replan/observation/failure via topics |
| 9 Telemetry | Failure topics observed by TelemetryService; telemetry does not gate autonomy |
| 11 SoT | Memory boundary doc reinforces WM / MemoryGraph / chat / derived views |
| 13 Host supremacy | Degrade modes; no cloud-required critical path |

## Historical gates

- ADR-006/012/013 preserved (no GoalEngine/PlanningEngine resurrection; no ReAct-in-orchestrator)
- ADR-018 B-primary: no LLM→TOOL_INVOKE bypass

## Regression

- Existing orchestrator/planner tests must remain green
- No CI bypass

## Out of scope (later PRs)

- Full TruthBoundary live wire / DecisionCard UI (021 M3–M5)
- Context builder WM-first assembly (020 M2)
- ADR-009 confirmation router implementation (018 M4)
- Model tier settings differentiation tests beyond docs (023 M2+)
