# ADR-002: Scheduler Model

**Status:** Proposed  
**Date:** 2026-07-09

## Context

Brain v1 must complete useful single-user work before supporting complex scheduling. Multiple concurrent goals would add coordination, cancellation, approval, and recovery complexity before the current workflow proves itself.

## Decision

Define `IScheduler` and implement `SingleGoalScheduler` after approval.

Only one goal may be active at a time. Additional goals queue and run sequentially.

## Rationale

- Single-active-goal scheduling matches the current single-user operating model.
- The scheduler interface avoids coupling the kernel to queue internals.
- Sequential execution makes approvals, correlation, and crash recovery easier to verify.

## Consequences

- No parallel goal execution in v1.
- Priority affects queued ordering before activation only.
- Pausing and cancellation are explicit scheduler operations.

## Verification

- Queue ordering is deterministic.
- Only one active goal exists at any time.
- Paused goals do not emit executable tasks.
