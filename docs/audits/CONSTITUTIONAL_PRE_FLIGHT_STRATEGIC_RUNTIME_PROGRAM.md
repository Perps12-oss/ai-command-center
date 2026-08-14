# Constitutional Pre-Flight — ACC Strategic Runtime & Architecture Completion Program

**Date:** 2026-08-14  
**Baseline:** `origin/main` @ `2f6c88b`  
**Branch:** `cursor/strategic-runtime-program-4cf5`  
**Authority:** `PROJECT_CONSTITUTION_V4.md`; Accepted ADRs; `docs/governance/IMPLEMENTATION_GUIDE.md`; `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`  
**Task class:** Governance / planned-work / architecture-program documentation. **No runtime product code in this change.**

---

## Scope

**In scope**

- Owner-authorized strategic posture: formerly “indefinitely gated” items become streams inside a controlled pipeline (Integration Proposal → ADR Decision → Section 9 → Implementation → Verification → Close-out).
- Phase 0 baseline: Strategic Gap Matrix (repository evidence).
- Program charter and Queue 1 update.
- Gate 1 Integration Proposal drafts for streams A–F (no implementation).
- Drop macOS Hotkey as a standalone strategic item.
- Name Cross-OS support as the **only remaining strategic gate**.

**Out of scope (this change)**

- Implementing streams A–F (explainability envelopes, autonomy thresholds, model orchestration M2–M4, EventBus pools, vector/federation live-wire, Goose code).
- Opening the Cross-OS gate.
- Amending `PROJECT_CONSTITUTION_V4.md`.
- Weakening UCGS (`scope_embeddings` S5 remains).
- Restoring OperatorKernel / GoalEngine / PlanningEngine / AgentCoordinator / PredictiveEngine / UndoReplay.
- Merging abandoned branch `cursor/phase5-async-eventbus-744e`.

---

## Article X

Product implementation of the six streams must not begin before this pre-flight **and** before each stream’s Gate 2 (ADR ACCEPT / REJECT / DEFER WITH EXPLICIT CONDITION) and Gate 3 (Section 9 plan). This PR is **not** stream implementation.

---

## Invariants / articles touched (docs only)

| Item | Effect |
|------|--------|
| Art. II hierarchy | Restated. Program is Queue 1 operational authority, not a new Art II level. |
| Art. V / Inv 11 single SoT | One canonical planned-work document remains `IMPLEMENTATION_GUIDE.md`. Program charter is subordinate. |
| Art. VII zero regression | No runtime behaviour change. |
| Art. IX non-circumvention | Pipeline **tightens** gates: “gated” means a named checkpoint, not a bypass. UCGS vector forbid unchanged. |
| Inv 13 host supremacy | Goose remains pattern adoption, not runtime SoT. Cross-OS stays last. |
| ADR-006 / 012 / 013 / 014 | Retired packages stay retired. |
| ADR-018–023 | Remain Accepted. Remaining Section 9 work enters the program; it does not silently become Queue 1 **code**. |
| PERFORMANCE_CONSTITUTION | Stream D must measure before isolation; constitution is verification authority, not a license to ship pools. |

---

## Hard stops checked

| Condition | Result |
|-----------|--------|
| Owner authorized replacing empty Queue 1? | **Yes.** This task is an explicit owner program, not invented tickets from `PLANNED_WORK_INVENTORY.md`. |
| Implementation against unresolved architecture? | **No.** Charter forbids stream code until Gate 2+3. |
| Vector DB / embeddings in this PR? | **No.** Stream E Gate 1 states SoT ADR first; UCGS S5 still blocks embeddings without enablement. |
| EventBus multi-pool in this PR? | **No.** Abandoned branch is not a merge candidate. Stage 1 is measurement after Gate 2. |
| macOS hotkey as Queue 1? | **No.** Dropped as a strategic item. Cross-OS remains gated. |
| Dual planning authority? | **Resolved:** Queue 1 names the program; historical inventories stay non-authoritative. |

---

## Decision

Proceed with documentation-only establishment of the program, Phase 0 gap matrix, and Gate 1 drafts.

**Do not** declare the six streams complete, Wave 0 complete on `main`, or Cross-OS opened from this branch tip (`PHASE_COMPLETION_RULE.md`).
