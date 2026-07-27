---
repository: block/goose
expedition_id: expedition-001-goose
decision_id: RD-001
---

# Research Decision Summary: Goose

## Decision

**Proceed** — Goose contains multiple engineering patterns suitable for adaptation into AI Command Center.

## Rationale

Goose is a mature Rust implementation of an MCP-first AI agent. Its provider abstraction, extension runtime, async session management, and configuration/secrets handling are reference-quality. The repository was chosen as the pilot expedition because it exercises the exact subsystems ACC is evolving: providers, extensions, tool execution, state/context, configuration, and observability.

The repository is **not** suitable as a wholesale architecture replacement. Its conversation-centric runtime, global singletons, and tightly coupled `Agent` object conflict with ACC's canonical authority chain and no-global-state rule. The value is in isolated patterns, not in adopting Goose as a system.

## Key Findings

- `Provider` trait + `MessageStream` offers a clean, provider-agnostic streaming contract.
- `ExtensionManager` demonstrates how to host, cache, and sandbox MCP extensions.
- `AgentManager` shows a correct pattern for per-session creation locks and bounded LRU caching.
- Cancellation-token registry per session is a simple, safe cancellation model.
- `Config` demonstrates layered precedence and migrations, but relies on global state.
- `context_mgmt` compaction uses message visibility metadata to preserve user-facing history.
- `tool_inspection.rs` provides a modular security/permission pipeline.
- Telemetry is well-layered (tracing, OTel, Langfuse, PostHog).

## Patterns Promoted

| Candidate | Pattern ID | Decision |
|-----------|------------|----------|
| C-001 | PAT-001 | Validate |
| C-002 | PAT-002 | Validate |
| C-003 | PAT-003 | Validate |
| C-004 | PAT-004 | Validate |
| C-005 | PAT-005 | Validate with adaptation |
| C-007 | PAT-006 | Validate |
| C-008 | PAT-007 | Validate |

## Patterns Held

| Candidate | Decision | Reason |
|-----------|----------|--------|
| C-006 | Hold | Needs deeper analysis of summarization model and state-authority impact. |
| C-009 | Hold | Conflicts with ACC Goal Scheduler scope; revisit if scheduling needs change. |
| C-010 | Hold | Out of current ACC UI scope. |

## Integration Proposals Generated

- INT-001 — Capability Provider Registry
- INT-002 — MCP Capability Runtime Adapter
- INT-003 — Session-scoped service creation locks and LRU cache
- INT-004 — Cancellation token registry for chat/tool operations
- INT-005 — Tool inspection and permission pipeline enrichment
- INT-006 — Settings migration and precedence layer
- INT-007 — Telemetry backend layering

## Next Steps

1. Review Integration Proposals in Architecture Review (Tom).
2. Convert approved proposals to ADRs in `docs/architecture/adr/`.
3. Do not begin runtime implementation until ADRs exist.
