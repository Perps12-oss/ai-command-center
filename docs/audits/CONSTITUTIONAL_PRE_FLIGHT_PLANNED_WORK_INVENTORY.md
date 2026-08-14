# Constitutional Pre-Flight — Planned Work Inventory

**STATUS:** HISTORICAL / NON-AUTHORITATIVE — pre-flight for the superseded inventory only.  
Do not implement from this document or from `PLANNED_WORK_INVENTORY.md`.

**Date:** 2026-08-12  
**Branch:** `cursor/planned-work-backlog-audit-4b28`  
**Baseline:** `origin/main` @ `b949f3e` (PR #170)  
**Authority:** `PROJECT_CONSTITUTION_V4.md` Art. X  
**Change type:** Documentation only (audit + index pointers)

---

## Scope

Produce a repository-truth inventory of:

- planned work that is not implemented on `origin/main`
- active backlogs
- work that was started, deferred, or displaced (scope creep)

No runtime, contract, topic, or composition-root changes.

## Protected assets

None modified.

## Sources of truth

Unchanged. This audit does not reassign ownership of World Model, MemoryGraph,
Settings, ExecutionAuthority, or EventBus topics.

## Invariants

| Invariant | Compliance |
|-----------|------------|
| 1 Ownership | Docs only; no new live path |
| 11 SoT | Inventory classifies Exists ≠ Wired ≠ Authoritative; does not treat plans as complete |
| 12 Non-circumvention | Does not weaken gates or hard stops |
| Art. X | Pre-flight recorded before the audit file |

## Historical gates

- Does not start Phase 5 Async EventBus (Performance Investigation Report + human approval)
- Does not re-wire OperatorKernel / GoalEngine / PlanningEngine / AgentCoordinator
- Does not implement from Proposed ADRs as if Accepted
- Does not declare any phase complete (PHASE_COMPLETION_RULE)

## Regression

Docs-only. Existing tests and CI gates are out of scope for this change.

## Out of scope

- Implementing any inventoried item
- Rewriting `MASTER_ROADMAP_2026.md` (recommended as a follow-on honesty pass)
- Opening GitHub issues (none exist in this repo today)
