# Pattern Registry

Canonical list of reusable engineering patterns extracted from external repositories.

| ID | Pattern | Source Repository | Status | Related RD | ADR |
|----|---------|-------------------|--------|------------|-----|
| PAT-001 | Declarative Provider Registry with Inventory State | block/goose | Validated | RD-001 | Pending |
| PAT-002 | MCP Extension Manager with Multi-Transport | block/goose | Hold | RD-001 | - |
| PAT-003 | Conversation Context Compaction with Visibility Metadata | block/goose | Validated | RD-001 | Pending |
| PAT-004 | Tool Inspector / Confirmation Router Pipeline | block/goose | Validated | RD-001 | Pending |
| PAT-005 | SQLite Session Storage with Schema Migrations | block/goose | Hold | RD-001 | - |
| PAT-006 | Modular Tool Inspection and Permission Pipeline | block/goose | Validated | RD-001 | Pending |
| PAT-007 | Layered Telemetry with Pluggable Backends | block/goose | Validated | RD-001 | Pending |

## Status values

- `Candidate` — extracted but not validated
- `Validated` — reviewed against ACC architecture and approved as a reusable pattern
- `Approved` — validated and passed Architecture Review (Tom)
- `Rejected` — evaluated and rejected with documented reason
- `Superseded` — replaced by a later pattern

## Files

- `patterns/index.md` — this registry
- `PAT-NNN.md` — validated pattern card

A `PAT-NNN.md` file is created only after validation. Candidates live in repository folders until promoted.
