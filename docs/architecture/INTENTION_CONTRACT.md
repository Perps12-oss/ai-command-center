# Intention Contract

**Status:** Binding (ADR-018 Section 9 M1)  
**Authority:** ADR-018 Tool Invocation Architecture  
**Related:** `ai_command_center/domain/intention.py`, `ai_command_center/core/intention_validation.py`

---

## Principle

The LLM never owns executable tool signatures. The planner emits **Intentions**; the orchestrator binds them to tools.

```text
Planner → Intention (capability + args)
    → ExecutionOrchestrator validates
    → TOOL_INVOKE / capability.runtime / llm.step
```

## Intention fields

| Field | Type | Meaning |
|-------|------|---------|
| `capability` | str | Catalog capability id (not freeform tool JSON) |
| `args` | dict | Capability arguments |
| `require_approval` | bool | HITL gate (copied from catalog / plan) |
| `step_id` | str | Plan step correlation |

`PlanStep` ↔ `Intention` via `Intention.from_plan_step` / `to_plan_step`.

## Validation classes (ADR-018 M2)

| Kind | Topic | Meaning |
|------|-------|---------|
| Parse | `tool.parse_failure` | Malformed intention payload (wrong shape; executable `tool` JSON rejected) |
| Validation | `tool.validation_failure` | Well-shaped but fails catalog / required-args rules |

Validation runs in `ExecutionOrchestratorService` **before** `TOOL_INVOKE`.

## Non-goals

- XGrammar / GBNF / logits processors
- LLM publishing directly to `TOOL_INVOKE`
