# Phase Plans Index

**STATUS:** INDEX of historical / parked / complete plans — **not** an implementation queue

Canonical planned-work document: [`docs/governance/IMPLEMENTATION_GUIDE.md`](../governance/IMPLEMENTATION_GUIDE.md) (Queue 1 = [Strategic Runtime Program](../governance/STRATEGIC_RUNTIME_PROGRAM.md)).  
Fossil index: [`docs/governance/HISTORICAL_AND_RETIRED_WORK.md`](../governance/HISTORICAL_AND_RETIRED_WORK.md)  
Disposition: [`docs/audits/FOSSIL_DISPOSITION_AUDIT.md`](../audits/FOSSIL_DISPOSITION_AUDIT.md)

This directory holds **phase plans**. Most are **HISTORICAL**. Agents must **not** plan implementation from PARTIAL/NOT_COMPLETE rows below.

**Hygiene:** `docs/governance/DOC_HYGIENE.md`  
**Latest code verification (historical 2026-07-20):** `docs/audits/PHASE_PLANS_ARCHIVE_VERIFICATION.md`  
**Inventory SoT (historical):** `docs/audits/REPOSITORY_TRUTH_CANON.md`  
**Truth matrix:** `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`

---

## Active milestone (current truth)

| Milestone | Document | Status |
|-----------|----------|--------|
| **PHASE R1 — Runtime Reconciliation** | [`PHASE_R1_RUNTIME_RECONCILIATION.md`](PHASE_R1_RUNTIME_RECONCILIATION.md) | **COMPLETE** on `main` (not Queue 1) |
| (superseded) PHASE 0R | [`PHASE_0R_REPOSITORY_TRUTH_RECONCILIATION.md`](PHASE_0R_REPOSITORY_TRUTH_RECONCILIATION.md) | HISTORICAL |

**Ungated Stage 2 / R1 disposition work is closed.** See [`docs/audits/R1_UNGATED_STOP_LINE.md`](../audits/R1_UNGATED_STOP_LINE.md).

**Superseded inventory (do not implement from):** [`docs/audits/PLANNED_WORK_INVENTORY.md`](../audits/PLANNED_WORK_INVENTORY.md)

**SA.mutate track CLOSED** (ADR-015/016/017). EventBus pools = **Stream D** (measure first). Goose = **Stream F**. Cross-OS = **Stream G** (only remaining strategic gate). macOS Hotkey strategic item **dropped**.

---

## Master Roadmap

| Document | Description |
|----------|-------------|
| `../MASTER_ROADMAP_2026.md` | **HISTORICAL** sequencing snapshot (2026-07-11). Not canonical. |

---

## Key Reference

| Document | Description |
|----------|-------------|
| `../architecture/UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md` | Phase B UI slices — **COMPLETE** on `main` (#105) |
| `../agents/DEVIN_UI_HANDOVER.md` | HISTORICAL Devin builder workflow |
| `../agents/CURSOR_AUDIT_GATE.md` | Cursor/Tom audit checklist per PR |
| `PHASE_7_8_9_10_QA.md` | HISTORICAL design Q&A |
| `IMPLEMENTATION_ORDER.md` | HISTORICAL ordering — not a completion record |

---

## Phase Plans (disposition 2026-08-12)

Statuses below are **fossil disposition**, not “keep active / implement next.”

| Phase | Document | Disposition | Archive? |
|-------|----------|-------------|----------|
| 5 | `PHASE_5_ASYNC_EVENTBUS_PLAN.md` | R4b single-queue **LIVE**; isolation = program **Stream D**; branch **ABANDONED** | Keep as historical (bannered) |
| 6 | `PHASE_6_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md` | Bridge **WIRED**; remaining MCP extras **not Queue 1** | Historical extras |
| 7 | ~~`PHASE_7_MULTI_AGENT_RUNTIME_PLAN.md`~~ | SUPERSEDED | [`../archive/PHASE_7_MULTI_AGENT_RUNTIME_PLAN_SUPERSEDED.md`](../archive/PHASE_7_MULTI_AGENT_RUNTIME_PLAN_SUPERSEDED.md) |
| 8 | `PHASE_8_OPERATOR_KERNEL_PLAN.md` | OperatorKernel **RETIRED** (ADR-006) | Historical |
| 8b | `PHASE_8_KNOWLEDGE_FEDERATION_PLAN.md` | Unified SoT / vectors **ABANDONED**; Stream E is SoT-first (new ADR) | Historical |
| 9 | `PHASE_9_GOALS_MULTI_AGENT_PLAN.md` | GoalEngine / PlanningEngine / AgentCoordinator **RETIRED** | Historical |
| 10 | `PHASE_10_WORLD_MODEL_PLAN.md` | WM core **LIVE**; Predictive/Undo **RETIRED** (ADR-014) | Historical |
| 11 platform | `PHASE_9_CROSS_PLATFORM_PLAN.md` | Cross-OS = **Stream G** (final gate); macOS hotkey strategic item **dropped**; Impl stubs **not** current work | Historical |

### Removed from active plans (do not plan from)

| Document | Archive class | Path |
|----------|---------------|------|
| Remaining Implementation Plan (2026-07-12) | STALE | [`../archive/REMAINING_IMPLEMENTATION_PLAN_2026-07-12_STALE.md`](../archive/REMAINING_IMPLEMENTATION_PLAN_2026-07-12_STALE.md) |

---

## Naming warning

| Label | Meaning |
|-------|---------|
| Phase 11 (this folder / master roadmap) | Cross-platform — **Stream G / not opened**; not Queue 1 code |
| Phase 11 frontend | `docs/PHASE_11_FRONTEND_IMPLEMENTATION.md` — UI 11A–11F largely on `main` |

Do not treat frontend Phase 11 completeness as cross-platform Phase 11 completeness.

---

## Phase Dependencies (informational / historical)

```
Phase 5 ──► Stream D (measure then ADR); R4b single-queue already live
Phase 6 ──► bridge wired; extras not Queue 1
Phase 8 ──► Operator Kernel RETIRED from live — ADR-006
Phase 9 ──► Goals ADR-012 A + Multi-Agent ADR-013 research-only
Phase 10 ─► World Model core live; Predictive/Undo RETIRED (ADR-014)
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
| 2026-08-12 | Fossil cleanup: canonical queue = Implementation Guide; plans are historical/parked/retired |
