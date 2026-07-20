# Phase 13 — Execution Resilience & Autonomous Operations

**Status:** FUTURE (deferred from Phase 12)  
**Dependencies:** Phase 12 State Intelligence (projection, idempotency, state deltas) proven stable  
**Authority:** `PROJECT_CONSTITUTION_V4.md` Articles XVIII–XIX

---

## Why deferred

Phase 12 establishes Reality + Intent, budgeted projection, capability selection, and write-through deltas.
Resilience and autonomy depend on that foundation.

---

## Scope (not implemented in Phase 12)

### 13A — Compensation & Rollback

- Every multi-step `ExecutionPlan` carries a compensation strategy
- On mid-plan failure: StateDeltaEngine computes a negative delta, or marks workspace `CORRUPTED`
- Saga-style retries where safe

### 13B — State Sentry

- Asynchronous drift detection between World Model and active goal trees
- External process/file/network changes update WM; Sentry alerts GoalScheduler to replan
- System-initiated self-correction without waiting for a user prompt

### 13C — Confidence-Based Reality Verification

- Nodes/edges carry `verified_at`, `confidence`, `verification_source` (fields seeded in Phase 12E.1)
- On planner query: if confidence below threshold → `RefreshProvider()` (lazy), not blanket TTL expiry
- Avoids expensive N-minute expiry of every node

---

## Non-goals for Phase 12

Do not implement compensation engines, sentry loops, or active refresh providers until Phase 12 slices land on `main`.
