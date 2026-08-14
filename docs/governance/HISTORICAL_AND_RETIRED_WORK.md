# Historical and Retired Work

**STATUS:** INDEX — not an implementation queue  
**Authority:** Derives from `PROJECT_CONSTITUTION_V4.md`, Accepted ADRs, and [`FOSSIL_DISPOSITION_AUDIT.md`](../audits/FOSSIL_DISPOSITION_AUDIT.md)  
**Canonical planned-work document:** [`IMPLEMENTATION_GUIDE.md`](IMPLEMENTATION_GUIDE.md) (Queue 1 = [Strategic Runtime Program](STRATEGIC_RUNTIME_PROGRAM.md))

When you encounter old code, old plans, or Proposed ADRs, read this index first.  
**These lists are not active implementation queues.**

---

## RETIRED ARCHITECTURE

Do not restore or wire into the current runtime without a **superseding** Accepted ADR.

| Package | Status | Binding ADR |
|---------|--------|-------------|
| OperatorKernel | RETIRED / NON-CANONICAL | ADR-006 — live intake = ExecutionAuthority |
| GoalEngine | RETIRED / NON-CANONICAL | ADR-012 — live = GoalRepository + SingleGoalScheduler |
| PlanningEngine | RETIRED / NON-CANONICAL | ADR-013 — live = PlannerService |
| AgentCoordinator | RETIRED / NON-CANONICAL | ADR-013 — live = AgentRuntimeService |
| PredictiveEngine | RETIRED / NON-CANONICAL | ADR-014 — research/unit-test tree only |
| UndoReplay | RETIRED / NON-CANONICAL | ADR-014 — live timeline/snapshots = TimelineService / SnapshotService / WM recover |

Packages may still exist on disk. **Exists ≠ Wired ≠ Authoritative.**

---

## ABANDONED PROGRAMS

| Program | Status |
|---------|--------|
| Chat C2–C4 as a modernization program | ABANDONED as a program. Live chat is the AppState / `chat.*` path. Do not treat remaining spec checklists as Queue 1. |
| Knowledge Federation as unified SoT / vectors | ABANDONED as a **vectors-as-SoT** program. Stream E of the Strategic Runtime Program may proceed only as **derived index** after a new ADR — never as SoT. |
| Insights as unfinished product | ABANDONED as a product ticket. UI placeholder is intentional empty state. |
| Goose extras / `provider_sdk` live-wire | ABANDONED as live-wire. Stream F may **Adapt** patterns only; Goose is not a runtime SoT. |
| macOS hotkey as a **strategic** item | **DROPPED**. Placeholder/`_start_tap()` log stub remain fossils. Not Queue 1. Hotkeys may return only as an optional Cross-OS **adapter** feature (Stream G). |

---

## PARKED IDEAS — NOT IMPLEMENTATION WORK

Items **moved into** [`STRATEGIC_RUNTIME_PROGRAM.md`](STRATEGIC_RUNTIME_PROGRAM.md) (checkpoints, not indefinite parking):

| Idea | Now |
|------|-----|
| EventBus pool isolation | Stream D — measurement then ADR; abandoned pool **branch** still not a merge candidate |
| Read-only FederationService | Stream E — after SoT ADR |
| ADR-021 ordinary-path DecisionRecord | Stream A — after Gates 2–3 |
| ADR-022 threshold escalation | Stream B — thresholds from Gate 2, then code |
| Goose pattern review | Stream F |

Still **not** in the six streams (remain parked / owner product):

| Idea | Gate |
|------|------|
| ADR-008 derived compaction | Owner product decision; ADR-020 forbids memory SoT |

Do **not** implement stream **code** from this table. Follow the program pipeline.

**Cross-OS (Stream G)** is the only remaining **strategic gate** — last, separate envelope.

---

## HISTORICAL BRANCHES

Remote heads below were **deleted** 2026-08-14. Do not recreate them as merge candidates.

| Branch | Status |
|--------|--------|
| `cursor/phase5-async-eventbus-744e` | **DELETED.** ABANDONED pool-isolation tree — **not a merge candidate**. Conflicts with #170 backpressure. Isolation tests would break single-queue FIFO. Stream D must not recover this branch. |
| `cursor/runtime-identity-loud-30d3` | **DELETED.** Unsubmitted fail-loud identity delta. Recreate from current `main` only if owner wants it. |
| `feature/planner-evolution-phase-c0-constitution` | **DELETED.** Stale 2026-07 planner C0 tree (~218 unique commits). Not a merge candidate. |
| `cursor/section9-handover-621d` | **DELETED** after porting the unique file to [`HANDOVER_SECTION9_TO_NEXT_AGENT.md`](../audits/HANDOVER_SECTION9_TO_NEXT_AGENT.md) (HISTORICAL / not Queue 1). |

Current main: `async_dispatch=True` **single** queue. Pool isolation is Stream D, not an incomplete-awaiting-merge branch.

---

## HISTORICAL ROADMAPS (not canonical)

These files still exist. They are **not** implementation queues:

- `docs/MASTER_ROADMAP_2026.md`
- `docs/architecture/ARCHITECTURE_TRANSITION_PLAN.md`
- `docs/architecture/PROVIDER_PLATFORM.md`
- `docs/architecture/UI_REFURBISHMENT_BACKLOG.md`
- `docs/architecture/UI_COMPONENT_SPECS/` (E05–E13 landed on `main`; Insights placeholder is intentional)
- `docs/audits/PLANNED_WORK_INVENTORY.md`
- `docs/audits/HANDOVER_SECTION9_TO_NEXT_AGENT.md` (HISTORICAL; do-not-regress facts in §4 only)
- `docs/PLACEHOLDER_AUDIT.md`
- `docs/plans/*` phase plans (bannered in place)

Canonical queue: [`IMPLEMENTATION_GUIDE.md`](IMPLEMENTATION_GUIDE.md) only.

---

## HOW TO READ CONFLICTING DOCUMENTS

See **How to Read This Repository** in [`IMPLEMENTATION_GUIDE.md`](IMPLEMENTATION_GUIDE.md).

Historical plans, retired packages, Proposed ADRs, research branches, and old inventories are **not** implementation authority.
