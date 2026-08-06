# ADR-023: Model Strategy

**Status:** Accepted — Brain independent (quality tiers as settings, not architecture)  
**Date:** 2026-08-05  
**Deciders:** Multi-council Architecture Decision Framework  
**Related:** Inv 13, ADR-007 Provider Registry, ModelRouterService, ARI  
**Framework:** `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`  
**Baseline:** `origin/main` @ `631b1f3`

---

## 1. Problem Statement

How much should ACC **architecture** depend on specific models or vendors?

A common proposal hard-wires capability tiers: local 3B for fast paths, `gpt-4o-mini` for replan, `gpt-4o` + human for WRITE_DESTROY reasoning. ACC’s ModelRouter today maps all tiers to `llama3.2:3b`. Coupling Brain correctness to cloud models violates host supremacy and makes the system untestable without vendors.

---

## 2. Current Repository

| Fact | Evidence |
|------|----------|
| ModelRouterService | Static map; no autonomous switching — [`model_router_service.py`](../../../ai_command_center/services/model_router_service.py) |
| DEFAULT_MODEL_TIER_MAP | fast/balanced/reasoning → `llama3.2:3b` — [`platform/model_registry.py`](../../../ai_command_center/platform/model_registry.py) |
| Settings defaults | `model_name` / `default_model` / `provider=ollama` — [`settings_snapshot.py`](../../../ai_command_center/domain/settings_snapshot.py) |
| Providers | OllamaHttpService + OpenAIHttpService wired; QwenPaw sidecar optional |
| ARI / Inv 13 | Externals are capabilities only; ACC owns UX/workspace/orchestration/memory SoT |
| Context over budget | Tier downgrade map reasoning→balanced→fast exists |

**Status:** Router is settings-shaped already; tier differentiation is empty. Brain does not require cloud.

---

## 3. Independent Review Proposal

Define real capability tiers: `fast` = local 3B; `balanced` = local + forced CoT; `reasoning` = cloud `gpt-4o-mini` for replan/stuck recovery; `critical` = `gpt-4o` + human for WRITE_DESTROY consequence reasoning. Invoke cloud when local confidence low or tier is destroy. Keep local-first but use cloud as mandatory “reasoning booster” for edge cases.

---

## 4. Architect Council

**Defense of Proposal A (capability-critical tier routing):**

- 3B models are weak at multi-step recovery; cloud models measurably help hard cases.
- Cost control: only pay when local confidence/tier requires it.
- Matches user mental model of “fast vs smart.”
- OpenAI path already exists — low incremental wiring cost.
- WRITE_DESTROY deserves maximum reasoning quality before HITL.

---

## 5. Red Team

| Axis | Attack |
|------|--------|
| Assumptions | Assumes architecture needs cloud for correctness; degrade modes can keep Brain running. |
| Scalability | Vendor rate limits, outages, and pricing become ACC availability. |
| Uniqueness | Same multi-model router story as every assistant. |
| Maintainability | Different models → different behaviors; golden tests fragment. |
| Production | Offline / air-gap / local-only users cannot use “critical” path. |
| Inv 13 | Cloud becomes de facto required for safe destroy / replan — host supremacy erosion. |

---

## 6. Alternative Architecture Team

**First principle:** Brain and runtime are **model-independent**.

```text
Brain / Orchestrator / WM / Policy
        │
        ▼
ModelRouter (settings-backed quality hints)
        │
        ▼
Provider adapters (Ollama, OpenAI, …) — capabilities only
```

- Model choice affects **reasoning quality**, not control flow authority.
- When models are weak/unavailable: capabilities **degrade** (narrower plans, more HITL, fail closed) — runtime contracts unchanged.
- Distinct tier model IDs may live in **settings** (`model_tier_map`) without architectural dependency on `gpt-4o`.
- No `critical = gpt-4o` rule in Brain code.

---

## 7. Systems Review Board

| Criteria | A Vendor-critical tiers | B Brain-independent |
|----------|-------------------------|---------------------|
| Simplicity | 2 | 4 |
| Performance | 4 (when cloud up) | 3 |
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
| Erode Workspace OS / Inv 13? | **A: Yes** if cloud required for Brain correctness. |
| Debt? | Hard-coded vendor model IDs in architecture. |
| Program separation? | Intelligence settings bleed into Automation authority. |
| Temporary as permanent? | “Just use gpt-4o for replan” becomes permanent coupling. |

Guardian **requires Accept B**; settings-backed quality maps are fine.

---

## 9. Council Decision

**Accept B (quality tiers as settings, not architecture).**

1. Brain / orchestrator / WM / policy must not hard-require a specific vendor model.
2. ModelRouter may resolve settings-backed `model_tier_map` differences (including cloud IDs the user configures).
3. Degrade modes when model weak/unavailable: more HITL, narrower plans, fail closed — **runtime unchanged**.
4. Reject architectural `critical = gpt-4o` (or any fixed cloud model) for WRITE_DESTROY / replan.
5. Aligns with ARI and Invariant 13.

---

## 10. Actionable Implementation Plan

| Milestone | Work | Tests / verification |
|-----------|------|----------------------|
| M1 | Document degrade modes (no model / weak model / provider error) in Model Orchestration + ARI cross-link | Doc + existing router tests |
| M2 | Allow settings `model_tier_map` values to differ per tier without Brain branching on vendor names | Settings + ModelRouter unit tests |
| M3 | Ensure replan / destroy paths work with local-only config (HITL instead of cloud requirement) | Integration test local-only |
| M4 | Telemetry: record selected model/provider/reason — never gate authority on cloud availability | Telemetry tests |
| Out of scope | Hard-coded gpt-4o critical tier; Brain calling OpenAI SDK directly | — |

**Dependencies:** ModelRouterService, SettingsSnapshot, ADR-019 replan (quality optional).  
**Migration:** Settings change only for users who want distinct tiers; defaults may remain local.

---

## References

- `docs/architecture/MODEL_ORCHESTRATION.md`
- `docs/architecture/AGENT_RUNTIME_INTERFACE.md`
- `docs/architecture/adr/ADR-007_PROVIDER_REGISTRY.md`
- `PROJECT_CONSTITUTION_V4.md` Invariant 13
- `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`
