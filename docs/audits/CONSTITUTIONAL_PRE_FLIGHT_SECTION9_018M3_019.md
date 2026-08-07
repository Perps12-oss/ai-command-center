# Constitutional Pre-Flight — Section 9 polish (018 M3 + 019 harden)

**Date:** 2026-08-06  
**Branch:** `cursor/section9-018m3-019-harden-621d`  
**Authority:** `PROJECT_CONSTITUTION_V4.md` Art. X; Accepted ADR-018 / ADR-019

## Scope

| ADR | Work |
|-----|------|
| 018 M3 | Refuse LLM→`TOOL_INVOKE` bypass: arch lint R5 (exclusive publisher = ExecutionOrchestrator) + tests |
| 019 | Richer `plan.replan.request` WM snapshot (`state_context`, observations, step_outputs, failed_step); multi-step fail→replan integration test |

## Protected assets

- EventBus topic semantics for `tool.invoke` / `plan.replan.*` (payload enrichment only)
- Intention → Orchestrator → ToolExecutor ownership (no new execution path)

## Sources of truth

- Unchanged: WM / MemoryGraph / Settings ownership
- Replan still EventBus-visible; PlannerService remains sole plan revision authority

## Invariants

| Invariant | Compliance |
|-----------|------------|
| 1 Ownership | Orchestrator exclusive `TOOL_INVOKE` publisher |
| 3 EventBus | Replan carries structured WM snapshot; no ReAct-in-orchestrator |
| 11 SoT | Snapshot is projection payload, not a new memory SoT |
| 13 Host | No cloud-required replan path |

## Out of scope

- Phase 5 Async EventBus (approval-gated)
- XGrammar / logits tool decode
- Live LLM planner assist wiring beyond PlannerService contracts
