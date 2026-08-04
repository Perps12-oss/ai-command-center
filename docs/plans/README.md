# Phase Plans Index

This directory contains **active or incomplete** implementation plans only.  
Completed / superseded / stale plans live in `docs/archive/`.

**Hygiene:** `docs/governance/DOC_HYGIENE.md`  
**Latest code verification:** `docs/audits/PHASE_PLANS_ARCHIVE_VERIFICATION.md`  
**Inventory SoT:** `docs/audits/REPOSITORY_TRUTH_CANON.md`  
**Truth matrix:** `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`

---

## Active milestone (current truth)

| Milestone | Document | Status |
|-----------|----------|--------|
| **PHASE R1 — Runtime Reconciliation** | [`PHASE_R1_RUNTIME_RECONCILIATION.md`](PHASE_R1_RUNTIME_RECONCILIATION.md) | P1–P4 ✅; P5 Predictive/Undo ✅ ADR-014 research-only |
| (superseded) PHASE 0R | [`PHASE_0R_REPOSITORY_TRUTH_RECONCILIATION.md`](PHASE_0R_REPOSITORY_TRUTH_RECONCILIATION.md) | — |

**Priority order (historical):** Runtime authority → Composition → State → UI → Features.

**Ungated Stage 2 / R1 disposition work is closed.** See [`docs/audits/R1_UNGATED_STOP_LINE.md`](../audits/R1_UNGATED_STOP_LINE.md).

**NEXT GATE:** SA.mutate for non-WM domains (new ADR). Parallel: Async EventBus (perf approval); Goose = Stage 3.

Goal: keep `origin/main` truthful (docs ↔ UI inventory ↔ runtime composition).

---

## Master Roadmap

| Document | Description |
|----------|-------------|
| `../MASTER_ROADMAP_2026.md` | Consolidated roadmap with all phases 1-11 |

---

## Key Reference

| Document | Description |
|----------|-------------|
| `../architecture/UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md` | **Phase B UI slices (Devin)** — PR-UI-E00…E13 |
| `../agents/DEVIN_UI_HANDOVER.md` | Devin builder workflow (stop → audit → continue) |
| `../agents/CURSOR_AUDIT_GATE.md` | Cursor/Tom audit checklist per PR |
| `PHASE_7_8_9_10_QA.md` | Design Q&A for Phases 7–10 (keep while phases incomplete) |
| `IMPLEMENTATION_ORDER.md` | Ordering recommendation only — not a completion record |

---

## Phase Plans (code-verified 2026-07-20)

Statuses below are from **repository code on `origin/main`**, not from legacy plan headers.

| Phase | Document | Code status | Archive? |
|-------|----------|-------------|----------|
| 5 | `PHASE_5_ASYNC_EVENTBUS_PLAN.md` | **PARTIAL** | No — keep active |
| 6 | `PHASE_6_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md` | **PARTIAL** | No — keep active |
| 7 | ~~`PHASE_7_MULTI_AGENT_RUNTIME_PLAN.md`~~ | NOT_COMPLETE / abandoned layout | **Archived SUPERSEDED** → [`../archive/PHASE_7_MULTI_AGENT_RUNTIME_PLAN_SUPERSEDED.md`](../archive/PHASE_7_MULTI_AGENT_RUNTIME_PLAN_SUPERSEDED.md) |
| 8 | `PHASE_8_OPERATOR_KERNEL_PLAN.md` | **PARTIAL** (not live intake) | No — keep active |
| 8b | `PHASE_8_KNOWLEDGE_FEDERATION_PLAN.md` | **NOT_COMPLETE** | No — keep active |
| 9 | `PHASE_9_GOALS_MULTI_AGENT_PLAN.md` | **PARTIAL** | No — keep active |
| 10 | `PHASE_10_WORLD_MODEL_PLAN.md` | **PARTIAL** | No — keep active |
| 11 platform | `PHASE_9_CROSS_PLATFORM_PLAN.md` | **NOT_COMPLETE** (stubs) | No — keep active |

### Removed from active plans (do not plan from)

| Document | Archive class | Path |
|----------|---------------|------|
| Remaining Implementation Plan (2026-07-12) | STALE | [`../archive/REMAINING_IMPLEMENTATION_PLAN_2026-07-12_STALE.md`](../archive/REMAINING_IMPLEMENTATION_PLAN_2026-07-12_STALE.md) |

**No Phase 5–10 plan was archived as COMPLETE** — code verification found zero COMPLETE_ON_MAIN plans.

---

## Naming warning

| Label | Meaning |
|-------|---------|
| Phase 11 (this folder / master roadmap) | Cross-platform macOS/Linux — **incomplete** |
| Phase 11 frontend | `docs/PHASE_11_FRONTEND_IMPLEMENTATION.md` — UI 11A–11F largely on `main` |

Do not treat frontend Phase 11 completeness as cross-platform Phase 11 completeness.

---

## Phase Dependencies (informational)

```
Phase 5 ──► later phases (Async EventBus — **approval-gated**)
Phase 6 ──► external capability aggregation
Phase 8 ──► Operator Kernel (**RETIRED from live — ADR-006**)
Phase 9 ──► Goals (**ADR-012 A**) + Multi-Agent (**ADR-013 research-only**)
Phase 10 ─► World Model core; Predictive/Undo **RETIRED from live (ADR-014)**
```

---

## Archive gate (reminder)

Before marking any plan COMPLETE and moving it to `docs/archive/`:

1. Verify against `origin/main` code (not a feature branch).
2. Record evidence in `docs/audits/`.
3. Follow `docs/governance/DOC_HYGIENE.md`.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial index created |
| 2026-07-20 | Code-verified statuses; archive Phase 7 SUPERSEDED + Remaining STALE; zero COMPLETE archives |
