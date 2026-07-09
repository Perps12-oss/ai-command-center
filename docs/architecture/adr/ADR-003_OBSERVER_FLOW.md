# ADR-003: Observer Flow

**Status:** Proposed  
**Date:** 2026-07-09

## Context

Filesystem, clipboard, and notification inputs can easily bypass architecture by writing state directly. ACC must let observers sense the outside world without making them authoritative.

## Decision

Observers emit raw `Observation` events to EventBus. Runtime decides whether an observation becomes a World Model mutation.

## Rationale

- Observers are source adapters, not domain owners.
- EventBus keeps signal flow visible and testable.
- Runtime remains the only component that applies World Model mutations.
- Startup sync and continuous monitoring can share one observation contract.

## Consequences

- Observers may keep transient debounce state only.
- Observers cannot import repositories or World Model mutation APIs.
- Runtime must validate observations before mutation.

## Verification

- File changes publish observations without direct persistence writes.
- Startup sync batches are chunked and correlated.
- Disabling an observer stops new observations without deleting World Model state.
