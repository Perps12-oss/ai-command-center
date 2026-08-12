# Fossil Disposition Audit

**STATUS:** HISTORICAL / NON-AUTHORITATIVE FOR IMPLEMENTATION  
**ROLE:** Fossil **disposition** authority (what to do with historical work) — **not** an implementation queue.

This document records previous investigation. It is not the current implementation plan.  
**Do not implement from this document.**

**Date:** 2026-08-12  
**Baseline:** `origin/main` @ `b949f3e` (PR #170)  
**Canonical planned-work queue:** [`docs/governance/IMPLEMENTATION_GUIDE.md`](../governance/IMPLEMENTATION_GUIDE.md)  
**Short fossil index:** [`docs/governance/HISTORICAL_AND_RETIRED_WORK.md`](../governance/HISTORICAL_AND_RETIRED_WORK.md)

---

## Verdict

Abandoning historical fossils does **not** regress current `main`. The live architecture is already established. The risk is the opposite: documents that look like “implement next.”

**Queue 1 after this disposition: EMPTY** of approved implementation work.

---

## A. LIVE / COMPLETE (do not describe as future work)

| Capability | Live path on `main` |
|------------|---------------------|
| R4b async EventBus | `create_application()` → `EventBus(..., async_dispatch=True)` — **single** `event-dispatch` queue |
| ExecutionAuthority intake | ADR-006; factory-wired |
| Receipts + TruthBoundary | Orchestration verification path |
| HITL confirmation | `tool.confirmation_*` + ApprovalsView (ADR-009 live-in-effect) |
| SingleGoalScheduler | Factory-wired; `Goal.depends_on` |
| World Model + SA mutate | ADR-015 memory, ADR-016 goals; ADR-017 WEA remain outside |
| Chat AppState path | `chat.*` reducers / StateApplier |
| Provider snapshot | `AppState.provider_registry` |
| Phase B UI program | COMPLETE on `main` (#105) |
| PHASE R1 | COMPLETE (P1–P5 disposition closed) |

Exists ≠ Wired ≠ Authoritative. The rows above are **wired**.

---

## B. LIVE-IN-EFFECT / DOCUMENTATION STATUS ONLY

Formal ADR **Status** remains **Proposed**. Do **not** silently mark Accepted.

| ADR | Disposition |
|-----|-------------|
| ADR-001 Persistence | LIVE-IN-EFFECT (SQLite / repositories) |
| ADR-002 Scheduler | LIVE-IN-EFFECT (`SingleGoalScheduler`) |
| ADR-003 Observer flow | LIVE-IN-EFFECT (observers → EventBus) |
| ADR-004 Runtime approval | LIVE-IN-EFFECT (security tiers + HITL) |
| ADR-009 Tool confirmation | LIVE-IN-EFFECT (confirmation topics + UI) |
| ADR-007b Provider registry | Live snapshot on AppState; Goose catalog extras obsolete |

---

## C. SUPERSEDED

| Item | Superseding authority |
|------|------------------------|
| ADR-005 as originally written | ADR-015–017 (WM / SA / scheduler split). **Do not Accept original wording.** |
| Retired intake (OperatorKernel / CommandRouter as live intake) | ADR-006 ExecutionAuthority |
| Old WM-as-sole-authority assumptions | ADR-015–017 |

---

## D. PARKED IDEA — NOT IMPLEMENTATION WORK

| Idea | Trigger / gate |
|------|----------------|
| Phase 5 multi-pool EventBus isolation | Measured single-queue contention; Art. VII/XII + owner approval |
| ADR-008 derived-view compaction | Owner product decision; ADR-020 forbids memory SoT |
| Read-only FederationService | Owner decision; not in factory |
| ADR-021 composed DecisionRecord on ordinary success/failure | Owner sequencing; not Queue 1 |
| ADR-022 threshold escalation | `AutonomyScore.compute` has threshold; orchestrator emits on approval + stuck only |

---

## E. GATED / OWNER DECISION REQUIRED

| Work | Gate |
|------|------|
| EventBus pool isolation | Performance Investigation Report + owner (not the historical PERF write-up arguing from plan) |
| ADR-022 threshold behaviour | Owner |
| ADR-008 acceptance/narrowing as product | Owner; still Proposed |
| macOS SKU | Phase 11 / owner SKU decision |
| Stage 3 Goose | Integration Proposal + ADR; Stage 3 checkpoint |

Do not put these in active implementation queues.

---

## F. ABANDONED / RETIRED

| Item | Status |
|------|--------|
| OperatorKernel live path | RETIRED (ADR-006) |
| GoalEngine live path | RETIRED (ADR-012) |
| PlanningEngine live path | RETIRED (ADR-013) |
| AgentCoordinator | RETIRED (ADR-013) |
| PredictiveEngine | RETIRED (ADR-014) |
| UndoReplay | RETIRED (ADR-014) |
| Unified knowledge federation / vectors-as-SoT | ABANDONED as program (constitutional vector gate) |
| Chat C2–C4 **as a program** | ABANDONED as a program (live chat is AppState path) |
| Phase 5 branch `cursor/phase5-async-eventbus-744e` | ABANDONED as merge candidate |
| Insights placeholder as unfinished product | ABANDONED as product ticket |
| Goose implementation extras / provider SDK live-wire | ABANDONED as current work |
| Fake/incomplete macOS CGEvent tap as current work | ABANDONED as current work (`_start_tap()` is a log stub) |

---

## G. HISTORICAL EVIDENCE

Audit reports, research notes, retired implementation notes, old investigations. Useful for provenance. **Not instructions.**

Includes: this file; `PLANNED_WORK_INVENTORY.md`; phase plans 5–10; `MASTER_ROADMAP_2026.md`; `PHASE_PLANS_ARCHIVE_VERIFICATION.md` (2026-07-20 baseline).

---

## Phase 5 (canonical wording)

- **Historical implementation / branch:** ABANDONED — **not a merge candidate**
- **Concept (multi-pool isolation):** PARKED
- **Current main:** `async_dispatch=True` single queue
- **Future trigger:** measured single-queue contention
- **Gate:** Art. VII/XII + owner approval

Do **not** describe the branch as incomplete, nearly complete, ready, next, pending, or awaiting merge unless explicitly qualified as historical.

---

## What this audit is not

It is not Queue 1. It does not authorize recovering the Phase 5 branch, restoring retired packages, or filling an empty queue with inventory UNGATED rows.
