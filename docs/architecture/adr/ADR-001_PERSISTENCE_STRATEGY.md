# ADR-001: Persistence Strategy

**Status:** Proposed  
**Date:** 2026-07-09

## Context

ACC is a single-user workspace operating system running on one machine. The World Model needs durable nodes, edges, and mutation replay without introducing operational complexity before there is evidence it is needed.

The Constitution requires repository ownership of persistence and exactly one source of truth per information domain.

## Decision

Use SQLite for Brain v1 persistence through repository interfaces only.

Define `IWorldModelRepository` for nodes, edges, transactions, and mutation journal operations. Implement the first version as `SQLiteWorldModelRepository`, an adapter over existing `EntityRepository` and `RelationshipRepository` plus a Brain-specific `mutation_journal`.

## Rationale

- SQLite solves the current single-user durability problem.
- Repository interfaces preserve future replacement paths.
- Reusing the entity/relationship graph preserves the existing World Model source of truth.
- JSON journal payloads keep v1 replay flexible without creating a second source of truth.
- Mutation journal replay supports crash recovery and traceability.

## Consequences

- Raw SQL outside repositories is forbidden.
- Planner, UI, observers, and capabilities cannot import persistence implementations.
- Future storage changes require new entity/relationship repository implementations plus a mutation journal migration plan.

## Verification

- Architecture lint rejects raw database access outside repositories.
- Crash recovery test replays the last five mutations.
- Correlation IDs appear in journal entries.
- Tests prove Brain nodes persist through `entities`, not parallel world-node tables.
