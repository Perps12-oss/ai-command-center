# ADR-005: World Model Authority

**Status:** Proposed  
**Date:** 2026-07-09

## Context

ACC already has a constitutional source-of-truth rule. Brain v1 depends on making that rule concrete for workspace reality so planners, observers, UI, and runtime do not each maintain competing state.

## Decision

The World Model is the sole source of truth for workspace reality.

No component may maintain authoritative state outside the World Model. Components may hold transient execution state or rebuildable projections only.

## Rationale

- A single authority prevents planner/UI/runtime drift.
- Crash recovery can rebuild from repositories and mutation journal.
- Future storage changes do not alter ownership.
- Chat remains an interface, not the system state.

## Consequences

- Observers observe.
- Planner reasons.
- Runtime executes.
- World Model stores.
- UI projects AppState.

Any component that stores durable workspace reality outside the World Model creates constitutional debt.

## Verification

- UI renders AppState projections only.
- Planner reads context and capability metadata only.
- Runtime is the only component that applies World Model mutations.
- Reboot recovery reconstructs the last known world state from repository data and journal.
