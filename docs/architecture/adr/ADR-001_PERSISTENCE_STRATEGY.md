# ADR-001: Persistence Strategy

**Status:** Proposed  
**Date:** 2026-07-09

## Context

ACC is a single-user workspace operating system running on one machine. The World Model needs durable nodes, edges, and mutation replay without introducing operational complexity before there is evidence it is needed.

The Constitution requires repository ownership of persistence and exactly one source of truth per information domain.

## Decision

Use SQLite for Brain v1 persistence through repository interfaces only.

Define `IWorldModelRepository` for nodes, edges, transactions, and mutation journal operations. Implement the first version as `SQLiteWorldModelRepository` after approval.

## Rationale

- SQLite solves the current single-user durability problem.
- Repository interfaces preserve future replacement paths.
- JSON attributes keep v1 schema flexible without creating a second source of truth.
- Mutation journal replay supports crash recovery and traceability.

## Consequences

- Raw SQL outside repositories is forbidden.
- Planner, UI, observers, and capabilities cannot import persistence implementations.
- Future storage changes require only a new repository implementation plus migration plan.

## Verification

- Architecture lint rejects raw database access outside repositories.
- Crash recovery test replays the last five mutations.
- Correlation IDs appear in journal entries.
