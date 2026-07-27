# Pattern Registry

Canonical list of reusable engineering patterns extracted from external repositories.

| ID | Pattern | Source Repository | Status | Related RD | ADR |
|----|---------|-------------------|--------|------------|-----|
| PAT-001 | Declarative Provider Registry with Inventory State | block/goose | Validated | RD-001 | [ADR-007](../../docs/architecture/adr/ADR-007_PROVIDER_REGISTRY.md) |
| PAT-002 | MCP Extension Manager with Multi-Transport | block/goose | Hold | RD-001 | - |
| PAT-003 | Conversation Context Compaction with Visibility Metadata | block/goose | Validated | RD-001 | [ADR-008](../../docs/architecture/adr/ADR-008_CONVERSATION_COMPACTION.md) |
| PAT-004 | Tool Inspector / Confirmation Router Pipeline | block/goose | Validated | RD-001 | [ADR-009](../../docs/architecture/adr/ADR-009_TOOL_CONFIRMATION_ROUTER.md) |
| PAT-005 | SQLite Session Storage with Schema Migrations | block/goose | Hold | RD-001 | - |
| PAT-006 | Modular Tool Inspection and Permission Pipeline | block/goose | Validated | RD-001 | [ADR-010](../../docs/architecture/adr/ADR-010_MODULAR_TOOL_INSPECTION.md) |
| PAT-007 | Layered Telemetry with Pluggable Backends | block/goose | Validated | RD-001 | [ADR-011](../../docs/architecture/adr/ADR-011_TELEMETRY_BACKENDS.md) |

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
