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
| Two documents both claim canonical planning authority | **Resolved by this cleanup.** One canonical plan = [`IMPLEMENTATION_GUIDE.md`](../governance/IMPLEMENTATION_GUIDE.md). `MASTER_ROADMAP_2026.md` and `PLANNED_WORK_INVENTORY.md` are bannered HISTORICAL / NON-AUTHORITATIVE. |
| Accepted ADR conflicts with live architecture | **No conflict found** that this docs pass would paper over. ADR-005 Proposed original wording is **not** Accepted. |
| Supposedly complete feature is unwired | R4b async single queue **is** wired (`application.py` `EventBus(..., async_dispatch=True)`). Tiered pools are **not** on main and will **not** be marked complete. |
| Genuinely active implementation work misclassified as abandoned | Queue 1 items 1–3 are complete on main. Phase 5 implement instruction is a fossil. Remaining inventory UNGATED rows are **not** promoted to Queue 1 (owner instruction: do not invent replacement work). |

---

## Decision

Proceed with documentation-only cleanup.

---

## Second pass (deep-dive)

After the first commit, a fresh search still found living documents that a competent LLM could treat as Queue 1. Closed in the follow-up commit (docs only):

- `DOC_HYGIENE.md` no longer tells implementers to plan from `docs/plans/`
- Phase B UI specs E05–E13 no longer say “pending merge”
- `PROVIDER_PLATFORM.md`, `UI_REFURBISHMENT_BACKLOG.md`, `PLACEHOLDER_AUDIT.md`, research backlog/registry bannered as not product Queue 1
- Truth matrix StateAuthority row no longer **PARTIAL** (WEA remain-outside is ADR-017, not a ticket)
- `ASYNC_EVENTBUS_POLICY.md` problem statement marked historical (pre-R4b)

Queue 1 remains **EMPTY**. No runtime edits.
