# Phase 12 — State Intelligence & Workspace Cognition

**Status:** IN PROGRESS  
**Priority:** HIGH  
**Dependencies:** State Authority migration on `main` (#80)  
**Authority:** `PROJECT_CONSTITUTION_V4.md` Articles XVIII–XIX, Invariant 14 (CAP-001)

---

## Mission

Transform the World Model from a post-execution record into the primary source of planning, context, memory, and decision support.

```text
Know → Project → Decide → Plan → Execute → Receipt → State Delta → World Model
```

---

## Slices

| ID | Component | Notes |
|----|-----------|-------|
| 12A | Governance completion | Memory UI → Authority; governance surface tests; NL classify; docs |
| 12B | WorldModelQueryService | Entity/relationship/timeline/goal/memory/app lookup |
| 12B.1 | Execution Intent Registry | Reality + Intent for projections |
| 12C | ContextProjectionService | Structured planner context from state |
| 12C.1 | ProjectionBudgetManager | Token budgets by priority |
| 12D | CapabilityRegistry | Workspace OS syscall table (`CapabilityDefinition`) |
| 12D.1 | CapabilitySelector | Context-filtered planner catalog |
| 12E | StateDeltaEngine | Receipts → state changes (not artifact spam) |
| 12E.1 | Graph-native edges | `status` / `confidence` / `verified_at` / `source` |
| 12F | IdempotencyService | WM + Intent checks before execute |
| 12F.1 | NO_OP path | `ExecutionResultType.NO_OP` / `SUCCESS_CACHED` |
| 12G | EpisodicReflectionService | Evidence-based post-run learning |
| 12H | Reconstruction suite | Survive total chat loss via World Model |

---

## Deferred — Phase 13

Compensation/rollback, State Sentry, confidence-based refresh loops.
See [PHASE_13_EXECUTION_RESILIENCE_PLAN.md](PHASE_13_EXECUTION_RESILIENCE_PLAN.md).

---

## Key modules

- `ai_command_center/capabilities/` — registry, selector, catalog v1
- `ai_command_center/core/state_intelligence/world_model_query_service.py`
- `ai_command_center/core/state_intelligence/execution_intent_registry.py`
- `ai_command_center/core/state_intelligence/context_projection_service.py`
- `ai_command_center/core/state_intelligence/projection_budget_manager.py`
- `ai_command_center/core/state_intelligence/idempotency_service.py`
- `ai_command_center/core/state_intelligence/state_delta_engine.py`
- `ai_command_center/core/state_intelligence/episodic_reflection_service.py`
- `ai_command_center/domain/execution_result_type.py`
