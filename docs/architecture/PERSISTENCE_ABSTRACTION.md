# Persistence Abstraction

**Status:** Proposed Phase 0 contract, pending approval  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `docs/ARCHITECTURE.md`, `docs/architecture/VNEXT_STATE_DRIVEN_BLUEPRINT.md`

## Principle

The World Model is the sole source of truth for workspace reality.

Observers observe. Planners reason. Runtime executes. World Model stores. UI projects.

No component may maintain authoritative workspace state outside the World Model. Derived caches and UI projections are allowed only when they can be rebuilt from repositories and the mutation journal.

## Repository constitution

All persistence access must occur through repositories.

Forbidden:

- Raw SQLite queries outside repository implementations.
- Direct database access from planners.
- Direct database access from capabilities.
- Direct database access from UI.
- Direct database access from observers.

Allowed:

- Composition root constructs repositories.
- Services receive repositories by injection.
- Tests may use repositories directly only for setup or verification.

## Core contracts

These are logical contracts. Python implementations should use `Protocol` or abstract base classes and existing domain dataclasses.

```text
Node
  id: string
  type: string
  attributes: object
  created_at: datetime
  updated_at: datetime

Edge
  id: string
  from_node_id: string
  to_node_id: string
  type: string
  attributes: object
  created_at: datetime

Mutation
  id: string
  correlation: CorrelationContext
  type: create_node | update_node | delete_node | create_edge | delete_edge
  payload: object
  created_at: datetime
```

```text
CorrelationContext
  correlation_id: string
  goal_id: string?
  action_id: string?
```

`CorrelationContext` is required on events, logs, journal entries, and action results from Phase 1 onward.

## IWorldModelRepository

```text
IWorldModelRepository
  begin_transaction() -> Transaction
  save_node(node: Node, correlation: CorrelationContext) -> void
  get_node(id: string) -> Node?
  delete_node(id: string, correlation: CorrelationContext) -> void
  save_edge(edge: Edge, correlation: CorrelationContext) -> void
  get_edges(node_id: string, direction: in | out | both) -> list[Edge]
  delete_edge(id: string, correlation: CorrelationContext) -> void
  append_mutation(mutation: Mutation) -> void
  list_mutations(limit: int, after_id: string?) -> list[Mutation]
  replay_mutations(limit: int) -> list[Mutation]
```

## Implementation v1: SQLite

Use SQLite as the only Phase 1 persistence implementation.

Tables:

- `entities` owned by `core/entity/entity_repository.py`
- `relationships` owned by `core/relationship/relationship_repository.py`
- `mutation_journal(id, correlation_id, goal_id, action_id, type, payload_json, created_at)`

`IWorldModelRepository` is an adapter over the existing entity graph, not a parallel node/edge store. `payload_json` keeps journal replay simple while preserving exact mutation identity, type, and payload.

Transactions use SQLite transactions through the repository only. The repository is responsible for atomic node, edge, and journal writes.

## Migration path

Future storage engines require a new `IWorldModelRepository` implementation, not changes to planners, runtime, observers, AppState, or UI.

The interface must remain storage-shaped around nodes, edges, transactions, and journal replay. Any later Postgres or graph-store implementation is earned only when SQLite no longer solves a demonstrated current problem.

## Verification

- Architecture lint must reject raw database imports outside repository modules.
- Runtime tests must prove journal replay can rebuild the last five mutations.
- Planner, UI, and capability modules must not import SQLite or repository implementation modules.
