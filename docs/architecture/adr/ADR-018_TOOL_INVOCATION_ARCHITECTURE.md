# ADR-018: Tool Invocation Architecture

**Status:** Accepted — Hybrid (B-primary)  
**Date:** 2026-08-05  
**Deciders:** Multi-council Architecture Decision Framework  
**Related:** ADR-006, ADR-009 (narrowed), ADR-004, `IMPLEMENTATION_TRUTH_MATRIX.md`  
**Framework:** `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`  
**Baseline:** `origin/main` @ `631b1f3`

---

## 1. Problem Statement

Should an LLM ever generate **executable** tool calls?

A common agent roadmap assumes grammar-constrained JSON (XGrammar / GBNF) so a model emits `{tool, arguments}` that the executor runs. ACC’s live path already routes capabilities through Planner → Orchestrator → ToolExecutor. Choosing wrong here either hardens commodity agent patterns into permanent architecture or wastes effort constraining the wrong interface.

---

## 2. Current Repository

Evidence only (`docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md` + code):

| Fact | Evidence |
|------|----------|
| Live intake | ExecutionAuthority → PlannerService / AgentRuntimeService → ExecutionOrchestrator → tools |
| Planner emits capabilities | `PlanStep(capability=…, args=…)` via deterministic `build_deterministic_plan` — [`ai_command_center/services/planner_service.py`](../../../ai_command_center/services/planner_service.py) |
| LLM plan JSON | `parse_structured_plan_response` exists; docstring: “LLM JSON parsing is Phase C follow-up”; not auto-driven by a live LLM planner service |
| Orchestrator | Sequential `_advance_run` publishes `TOOL_INVOKE` with `tool: step.capability` — [`execution_orchestrator_service.py`](../../../ai_command_center/services/execution_orchestrator_service.py) |
| ToolSpec | `name`, `description`, `handler` — no input JSON Schema field — [`core/tools.py`](../../../ai_command_center/core/tools.py) |
| ToolExecutor | Registry lookup + handler; no decode-time grammar — [`tools/tool_executor.py`](../../../ai_command_center/tools/tool_executor.py) |
| Grammar / XGrammar / GBNF | Absent in repo |
| ADR-009 | Proposed ToolConfirmationRouter assuming LLM-generated tool calls |

**Status:** LLM does **not** own executable tool calls on the live path. Planner emits intentions (capabilities).

---

## 3. Independent Review Proposal

Integrate grammar-constrained decoding (XGrammar or llama.cpp GBNF) into the execution path so the LLM’s logits are restricted to valid tool-call JSON. Add distinct metrics: `tool_parse_failure` (malformed JSON) vs `tool_validation_failure` (valid JSON, invalid business args). Treat structured tool emission by the model as the primary tool-invocation architecture.

---

## 4. Architect Council

**Defense of Proposal A (grammar-constrained LLM tool calls):**

- Small local models (e.g. 3B) have weak JSON adherence; unconstrained decoding fails under pressure.
- Constraining the token manifold at sample time turns “please emit valid JSON” into a hard law.
- Separating parse vs validation metrics diagnoses schema vs logic failures.
- Industry agents (Goose, OpenHands-style loops) already assume model→tool JSON; ACC would gain interoperability and library leverage.
- Instrumentation is cheap relative to endless regex cleanup.

---

## 5. Red Team

**Attack on Proposal A:**

| Axis | Attack |
|------|--------|
| Assumptions | Assumes the LLM *should* emit executables. ACC’s live path already proved capability intents work without that. |
| Scalability | Grammar per tool / union grammars explode as capability catalog grows; MCP tools multiply surface. |
| Uniqueness | Makes ACC a chatbot-agent with tools — opposite of Workspace OS. |
| Maintainability | Couples inference backend (Ollama today has no logits processor API) to planning; forces llama.cpp/vLLM migration for “correctness.” |
| Production | False sense of safety: syntactically valid `rm`-shaped args still need sandbox/tiers; grammar ≠ policy. |
| Ownership | Dual path: LLM→executor vs Planner→orchestrator splits authority (ADR-006 risk). |

---

## 6. Alternative Architecture Team

**First principle:** The LLM never knows tool signatures as executable contracts.

```text
User / Goal
    → Planner emits Intention (capability id + typed args)
    → Runtime / Orchestrator selects and binds tools
    → ToolExecutor runs handlers
    → Sandbox + SecurityTier + PermissionService gate execution
```

- Capability catalog owns schemas and risk metadata.
- LLM may assist Planner with *intentions* only through `PlannerService` contracts — never publish raw tool JSON to `TOOL_INVOKE`.
- Validation metrics attach to **intention** payloads, not model freestyle tool blocks.
- No XGrammar/llama.cpp required for tool invocation correctness.

This is not “Proposal A with validation.” It inverts who owns executability.

---

## 7. Systems Review Board

Scores: 1–5 (higher better), except Production Risk (1 = low risk, 5 = high risk).

| Criteria | A Grammar LLM tools | B Intention → Runtime |
|----------|---------------------|------------------------|
| Simplicity | 2 | 4 |
| Performance | 3 | 4 |
| Reliability | 3 | 4 |
| Local LLM | 2 (needs new runtime) | 5 |
| Testability | 3 | 5 |
| Extensibility | 3 | 4 |
| Uniqueness (Workspace OS) | 1 | 5 |
| Production Risk | 4 | 2 |

---

## 8. Constitution Guardian

| Question | Finding |
|----------|---------|
| More like every other AI assistant? | **A: Yes.** Model→tool JSON is commodity agent shape. |
| Erode Workspace OS? | **A: Yes.** Chat/LLM becomes the execution author. |
| Architectural debt? | **A: Yes** if added beside Planner without retiring it (dual authority). |
| Weaken Program separation? | **A: Risk** — inference platform work bleeds into automation Program. |
| Temporary as permanent? | Grammar as “fix parse failures” becomes permanent coupling to a specific decoder. |
| Inv 1–3 / 11 / 13? | A pressures Inv 11 (who owns tool contract?) and Inv 13 if cloud/grammar server becomes SoT for valid actions. **B aligns.** |

Guardian **conflicts with Accepting A as primary architecture**. Hybrid allowed if B remains primary.

---

## 9. Council Decision

**Hybrid → B-primary.**

1. Canonical tool invocation remains: **Planner intentions → Orchestrator → ToolExecutor**.
2. LLM must **not** publish executable tool calls directly to the executor.
3. Optional LLM **planner assist** may produce intention structures only via `PlannerService`.
4. Do **not** adopt XGrammar/llama.cpp for tool logits as architecture.
5. ADR-009 is **narrowed**: confirmation/HITL apply to capability/intention execution and existing approval topics — not to a model-owned tool-call stream as the primary design.

---

## 10. Actionable Implementation Plan

| Milestone | Work | Tests / verification |
|-----------|------|----------------------|
| M1 | Document intention contract: capability id + args owned by capability catalog; map `PlanStep` ↔ intention | Contract doc + unit tests for PlanStep validation |
| M2 | Add schema validation on intention args before `TOOL_INVOKE`; emit distinct telemetry: `tool_parse_failure` (malformed intention payload) vs `tool_validation_failure` (schema/business rule) | Unit + telemetry topic tests |
| M3 | If LLM planner assist lands: only through `PLAN_REQUEST` / PlannerService; refuse raw LLM→`TOOL_INVOKE` bypass (arch lint / test) | Arch lint or service test |
| M4 | Narrow ADR-009 implementation (follow-on): align confirmation with `require_approval` / permission / Brain tiers — not Goose-style model tool_call_id as sole key | ADR-009 update PR |
| Out of scope | XGrammar, GBNF server, logits processors | — |

**Dependencies:** ADR-006 live path; ToolExecutorService; capability catalog.  
**Migration:** No dual path; no retirement of PlannerService. Existing deterministic planner remains valid.

---

## References

- `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`
- `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`
- `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`
- `docs/architecture/adr/ADR-009_TOOL_CONFIRMATION_ROUTER.md`
- `docs/architecture/WORKSPACE_VISION.md`
