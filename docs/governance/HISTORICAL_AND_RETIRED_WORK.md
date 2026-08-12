# Historical and Retired Work

**STATUS:** INDEX — not an implementation queue  
**Authority:** Derives from `PROJECT_CONSTITUTION_V4.md`, Accepted ADRs, and [`FOSSIL_DISPOSITION_AUDIT.md`](../audits/FOSSIL_DISPOSITION_AUDIT.md)  
**Canonical planned-work document:** [`IMPLEMENTATION_GUIDE.md`](IMPLEMENTATION_GUIDE.md)

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
| Knowledge Federation as unified SoT / vectors | ABANDONED as a program. Vector DB remains constitutionally gated. |
| Insights as unfinished product | ABANDONED as a product ticket. UI placeholder is intentional empty state. |
| Goose extras / `provider_sdk` live-wire | ABANDONED as current work. Live substitute = AppState provider snapshot. |
| macOS hotkey Impl as current work | ABANDONED as current work. `get_hotkey_provider()` returns a placeholder; `_start_tap()` is a log stub. SKU decision is GATED. |

---

## PARKED IDEAS — NOT IMPLEMENTATION WORK

| Idea | Gate |
|------|------|
| EventBus pool isolation (Phase 5 tiered dispatch) | Measured single-queue contention; Art. VII/XII + owner approval |
| ADR-008 derived compaction | Owner product decision; ADR-020 forbids memory SoT |
| Read-only FederationService | Owner; type exists, **not** in factory |
| ADR-021 composed DecisionRecord on ordinary success/failure | Owner sequencing |
| ADR-022 threshold escalation | Owner; not Queue 1 |

**STATUS: PARKED.** Do not implement without owner approval and the named gate.

---

## HISTORICAL BRANCHES

| Branch | Status |
|--------|--------|
| `cursor/phase5-async-eventbus-744e` | ABANDONED — **not a merge candidate**. Conflicts with #170 backpressure. Isolation tests would break single-queue FIFO. |

Current main: `async_dispatch=True` **single** queue. The branch is not incomplete-awaiting-merge.

---

## HISTORICAL ROADMAPS (not canonical)

These files still exist. They are **not** implementation queues:

- `docs/MASTER_ROADMAP_2026.md`
- `docs/architecture/ARCHITECTURE_TRANSITION_PLAN.md`
- `docs/audits/PLANNED_WORK_INVENTORY.md`
- `docs/plans/*` phase plans (bannered in place)

Canonical queue: [`IMPLEMENTATION_GUIDE.md`](IMPLEMENTATION_GUIDE.md) only.

---

## HOW TO READ CONFLICTING DOCUMENTS

See **How to Read This Repository** in [`IMPLEMENTATION_GUIDE.md`](IMPLEMENTATION_GUIDE.md).

Historical plans, retired packages, Proposed ADRs, research branches, and old inventories are **not** implementation authority.
