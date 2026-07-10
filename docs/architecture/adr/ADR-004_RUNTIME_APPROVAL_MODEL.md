# ADR-004: Runtime Approval Model

**Status:** Proposed  
**Date:** 2026-07-09

## Context

Brain v1 must execute useful actions while protecting user data. The runtime needs a simple, inspectable safety model before adding richer automation.

## Decision

Use three security tiers:

- `READ`
- `WRITE`
- `WRITE_DESTROY`

`WRITE_DESTROY` requires explicit local approval. Approval timeout is 60 seconds and denies the action.

## Rationale

- Three tiers are enough for v1 user-visible safety.
- Deny-on-timeout is conservative and predictable.
- Approval decisions become traceable with `CorrelationContext`.
- The same approval interface can support CLI or UI prompts.

## Consequences

- Actions without a declared tier are rejected.
- Runtime must emit `ActionResult` for approved, denied, failed, cancelled, and timed-out actions.
- No automatic retry for `WRITE` or `WRITE_DESTROY` in v1.

## Verification

- Destructive action cannot run without approval.
- Approval timeout produces a denied action result.
- Runtime logs and journal entries share the same correlation ID.
