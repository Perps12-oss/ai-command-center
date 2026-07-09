# Observer Framework

**Status:** Proposed Phase 0 contract, pending approval  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `docs/ARCHITECTURE.md`, `docs/architecture/VNEXT_STATE_DRIVEN_BLUEPRINT.md`

## Purpose

Observers turn external signals into raw observations. They do not update the World Model, write repositories, call planners, or execute actions.

Required flow:

```text
Observer -> Observation event -> EventBus -> Runtime -> World Model -> AppState -> UI
```

## Lifecycle

### Startup Sync

At startup, each observer may emit a bounded batch of current state.

Rules:

- Batch observations must be tagged as `mode=startup_sync`.
- Large sources must be chunked.
- Startup sync must not block UI startup.
- Startup sync emits observations only; runtime decides whether and how to mutate the World Model.

### Continuous Monitoring

After startup sync, observers switch to throttled continuous monitoring.

Rules:

- Repeated changes must be coalesced.
- Observers must apply local backpressure.
- Observers must not retry forever on inaccessible sources.
- Observers must publish errors as observation failures, not throw into UI.

## Observation contract

```text
Observation
  id: string
  source: filesystem | clipboard | notification | other
  mode: startup_sync | continuous
  observed_at: datetime
  subject: string
  change_type: created | updated | deleted | moved | snapshot | error
  raw_payload: object
  correlation: CorrelationContext
```

`raw_payload` is intentionally source-shaped. Runtime translates observations into validated world mutations.

## IObserver

```text
IObserver
  name: string
  start(correlation: CorrelationContext) -> void
  stop(correlation: CorrelationContext) -> void
  snapshot(correlation: CorrelationContext) -> list[Observation]
  health() -> ObserverHealth
```

## Implementation v1

Implement only local single-machine observers:

- Filesystem observer for configured workspace roots.
- Clipboard observer for explicit user-enabled clipboard capture.
- Notification observer only when the host platform already exposes a simple local API.

The filesystem watcher implementation must be hidden behind `IObserver`; no other component depends on a watcher library.

## Critical constraints

- Observers emit raw observations.
- EventBus transports observations.
- Runtime applies approved observations to the World Model.
- World Model remains the source of truth.
- UI renders AppState projections only.

## EventBus behavior

Proposed topics for Phase 1 contract registration:

```text
observation.received
observation.batch_received
observation.failed
observer.started
observer.stopped
observer.error
```

All payloads require `CorrelationContext`.

## Forbidden behavior

- Observers must not import repositories.
- Observers must not write SQLite.
- Observers must not call World Model mutation methods.
- Observers must not call planners.
- Observers must not call tools.
- Observers must not own authoritative state.

## Verification

- A file creation emits `observation.received` and does not write persistence directly.
- Startup sync emits a batch without blocking service startup.
- Duplicate rapid changes are coalesced before runtime receives them.
- Disabling an observer stops continuous events but does not delete World Model state.
