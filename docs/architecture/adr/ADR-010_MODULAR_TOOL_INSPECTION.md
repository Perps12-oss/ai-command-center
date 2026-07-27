# ADR-010: Modular Tool Inspection and Permission Pipeline

**Status:** Proposed  
**Date:** 2026-07-27  
**Deciders:** Architecture Review (Tom)  
**Supersedes:** —  
**Related:** `research/patterns/PAT-006.md`, `research/integration/INT-005.md`, `research/decisions/RD-001.md`, `docs/architecture/ADR-004_RUNTIME_APPROVAL_MODEL.md`, `ADR-009_TOOL_CONFIRMATION_ROUTER.md`

---

## Context

Tool calls need pre-execution checks for prompt injection, data egress, adversarial inputs, and repetitive loops. ACC's `ToolExecutorService` has basic permission and sandbox checks, but they are not pluggable. `block/goose` runs a `ToolInspectionManager` with ordered inspectors, each returning `Allow`, `RequireApproval`, or `Block`.

## Decision

Add a **ToolInspectionService** that runs a configurable pipeline of inspectors before `ToolExecutorService` dispatches a tool call. Inspectors are pure functions/objects that receive the tool call context and return an `InspectionResult`. The pipeline result feeds into `ADR-009` when approval is required.

### Contract

- `tool.inspection` — emitted with inspector findings.
- `tool.failed` — emitted when an inspector returns `Block`.
- `tool.confirmation_required` — emitted when an inspector returns `RequireApproval` (handled by `ADR-009`).
- `tool.started` — emitted only when all inspectors return `Allow`.
- Inspectors are loaded from settings; order is deterministic.
- `PermissionService` stores per-tool `PermissionLevel` (`AlwaysAllow`, `AllowOnce`, `Ask`, `NeverAllow`) and is consulted by the permission inspector.

## Rationale

| Factor | Without inspection pipeline | With inspection pipeline |
|--------|-----------------------------|--------------------------|
| Defense in depth | Hard-coded checks only | Pluggable security, egress, adversary, repetition checks |
| Testability | Mixed in executor | Each inspector is independently unit-testable |
| Flexibility | All-or-nothing | Individual inspectors can be enabled/disabled per deployment |
| Approval flow | Executor decides alone | Findings drive `ADR-009` confirmation router |

## Consequences

### Positive

- Security, egress, adversarial, and repetition checks are independent and testable.
- New inspectors can be added without changing the dispatch path.
- User approval is explicit and persistent.

### Negative / Risk

- False positives can block legitimate tools.
- Inspector ordering matters and must be deterministic.
- `AlwaysAllow` must be revocable by the user.

## Implementation Notes

- `ToolInspectionService` is called by `ToolExecutorService` before dispatch.
- Inspector interface: `inspect(tool_name, arguments, session, context) -> InspectionResult(Allow | RequireApproval | Block, message, metadata)`.
- Adversary inspector is opt-in due to LLM latency/cost.
- Telemetry events include inspector findings for auditability.

## Verification

- Unit test: each inspector returns correct `InspectionResult`.
- Test: pipeline order is deterministic and configurable.
- Test: `Block` stops execution before dispatch.
- Test: `RequireApproval` routes through `ADR-009` confirmation router.
