# Research Decisions for block/goose

## RD-001: block/goose Expedition Outcome

- **Repository:** block/goose
- **Decision:** Proceed
- **Date:** 2026-07-27

### Rationale

block/goose is a mature Rust implementation of a desktop AI agent. It does not match ACC's Workspace OS architecture, but it contains several well-engineered patterns that can strengthen ACC when adapted:

1. Provider registry with inventory state (PC-001)
2. Conversation context compaction (PC-003)
3. Tool inspection / confirmation router (PC-004)
4. Modular tool inspection and permission pipeline (PAT-006)
5. Layered telemetry with pluggable backends (PAT-007)

These patterns can be integrated into ACC's EventBus/AppState/service layers without weakening execution authority.

### Patterns promoted

| Candidate | Status | Pattern ID |
|-----------|--------|------------|
| PC-001 | Validated | PAT-001 |
| PC-002 | Hold | - |
| PC-003 | Validated | PAT-003 |
| PC-004 | Validated | PAT-004 |
| PC-005 | Hold | - |
| PAT-006 (existing) | Validated | PAT-006 |
| PAT-007 (existing) | Validated | PAT-007 |

### Integration proposals

- INT-001: Provider Registry Snapshot in AppState (from PAT-001)
- INT-005: Tool Inspection and Permission Pipeline Enrichment (from PAT-006)
- INT-007: Telemetry Backend Layering (from PAT-007)

### ADRs drafted (after Architecture Review by Tom)

| Pattern | ADR |
|---------|-----|
| PAT-001 | [ADR-007: Provider Registry Snapshot in AppState](../../docs/architecture/adr/ADR-007_PROVIDER_REGISTRY.md) |
| PAT-003 | [ADR-008: Conversation Context Compaction with Visibility Metadata](../../docs/architecture/adr/ADR-008_CONVERSATION_COMPACTION.md) |
| PAT-004 | [ADR-009: Tool Confirmation Router Pipeline](../../docs/architecture/adr/ADR-009_TOOL_CONFIRMATION_ROUTER.md) |
| PAT-006 | [ADR-010: Modular Tool Inspection and Permission Pipeline](../../docs/architecture/adr/ADR-010_MODULAR_TOOL_INSPECTION.md) |
| PAT-007 | [ADR-011: Layered Telemetry Backends](../../docs/architecture/adr/ADR-011_TELEMETRY_BACKENDS.md) |

### Next steps

- Move ADRs to `Accepted` status after final architecture sign-off.
- Produce implementation plans and schedule work against the architecture transition backlog.
- Keep PC-002 and PC-005 in backlog for future expeditions.
