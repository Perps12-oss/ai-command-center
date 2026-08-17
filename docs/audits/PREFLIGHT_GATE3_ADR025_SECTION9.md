# Constitutional Pre-Flight — Gate 3 ADR-025 §9 (Goose Adapt)

**Date:** 2026-08-17  
**Authority:** Article X; `PROJECT_CONSTITUTION_V4.md`; Accepted [`ADR-025_GOOSE_PATTERN_ADOPTION.md`](../architecture/adr/ADR-025_GOOSE_PATTERN_ADOPTION.md); [`STRATEGIC_RUNTIME_PROGRAM.md`](../governance/STRATEGIC_RUNTIME_PROGRAM.md) Wave 4; [`IMPLEMENTATION_GUIDE.md`](../governance/IMPLEMENTATION_GUIDE.md) Queue 1; Inv 13 / Rule 2 / Rule 3.  
**Implementation start:** blocked until this file exists. This change is **docs-only Gate 3** — no Stream F product code.

## What this change is

Add ADR-025 **§9 Gate 3 — Section 9 Implementation Plan (F1–F4)** for all four Goose **Adapt** rows, with files, interfaces, migrations, tests, wiring, docs, acceptance, rollback, Wave 4 sequential roadmap, and Gate 4 exit criteria. Update the Adoption Record and Queue 1 Wave 4 status pointers.

## What this change is not

- Not Gate 4 product code.
- Not Goose code import, Electron UI, globals, MCP-as-SoT, or any Reject-row pattern.
- Not Stream D isolation, Stream E embeddings, or Stream G / Wave 6.
- Not Wave 4 complete (Gate 4–6 remain after this plan lands on `main`).

## Invariants

Pattern adoption only. Each Adapt row has its own F* field table. No new EventBus topics invented in this docs PR. No `provider_sdk` live-wire.
