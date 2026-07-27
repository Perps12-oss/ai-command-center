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

### Next steps

- Draft ADRs for PAT-001, PAT-003, PAT-004, PAT-006, and PAT-007 after Architecture Review (Tom).
- Keep PC-002 and PC-005 in backlog for future expeditions.
