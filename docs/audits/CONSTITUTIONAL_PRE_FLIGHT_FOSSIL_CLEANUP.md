# Constitutional Pre-Flight — Canonical Repository / Fossil Cleanup

**Date:** 2026-08-12  
**Baseline:** `origin/main` @ `b949f3e` (PR #170)  
**Branch:** `cursor/canonical-fossil-cleanup-4b28`  
**Authority:** `PROJECT_CONSTITUTION_V4.md`; Accepted ADRs; `docs/governance/IMPLEMENTATION_GUIDE.md`  
**Disposition authority for fossils:** `docs/audits/FOSSIL_DISPOSITION_AUDIT.md`

---

## Scope

Documentation / repository hygiene / governance cleanup only.

**In scope:** planning docs, ADR status honesty (without silently Accepting Proposed ADRs), historical banners, one canonical planned-work queue, fossil index.

**Out of scope:** product functionality, EventBus architecture changes, receipts / TruthBoundary / HITL, scheduler / WM authority, OperatorKernel / GoalEngine / PlanningEngine / PredictiveEngine / UndoReplay resurrection, ADR-008/010/011/021/022 implementation, federation, macOS SKU, runtime refactors.

---

## Article X

Implementation of product code must not begin before this pre-flight. This task is **not** product implementation. No runtime modules will be edited.

---

## Invariants / articles touched (docs only)

| Item | Effect of this change |
|------|------------------------|
| Art. II hierarchy | Restated, not amended. No new Level labels. |
| Inv. 11 / Art. V single SoT | One canonical planned-work document; historical inventories demoted. |
| Art. VII zero regression | No runtime behaviour change. |
| Art. IX non-circumvention | No gate weakening. |
| ADR-006 / 012 / 013 / 014 | Retired packages labelled RETIRED; not re-wired. |
| ADR-015–017 | Live authority split left unchanged; ADR-005 marked SUPERSEDED rather than Accepted. |

---

## Hard stops checked

| Condition | Result |
|-----------|--------|
| Current main contradicts fossil disposition on **runtime authority** | **No.** Live intake = ExecutionAuthority; EventBus = `async_dispatch=True` single queue; WM + SA mutate per 015/016; WEA out per 017. |
| Cleanup requires production code | **No** for the planned edits. UCGS profile still contains CommandRouter pipeline strings — reported, not silently “fixed” in yaml (see remaining ambiguities). |
| Two documents both claim canonical planning authority | **Yes, today** (`IMPLEMENTATION_GUIDE.md` Queue 1 vs `MASTER_ROADMAP_2026.md` “authoritative roadmap” vs `PLANNED_WORK_INVENTORY.md` UNGATED list). Cleanup resolves this: one canonical plan = Implementation Guide. |
| Accepted ADR conflicts with live architecture | **No conflict found** that this docs pass would paper over. ADR-005 Proposed original wording is **not** Accepted. |
| Supposedly complete feature is unwired | R4b async single queue **is** wired (`application.py` `EventBus(..., async_dispatch=True)`). Tiered pools are **not** on main and will **not** be marked complete. |
| Genuinely active implementation work misclassified as abandoned | Queue 1 items 1–3 are complete on main. Phase 5 implement instruction is a fossil. Remaining inventory UNGATED rows are **not** promoted to Queue 1 (owner instruction: do not invent replacement work). |

---

## Decision

Proceed with documentation-only cleanup.
