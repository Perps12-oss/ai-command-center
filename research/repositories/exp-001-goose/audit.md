# Tom Architecture Review — Goose Expedition (exp-001)

**Scope:** Validated patterns from `block/goose` and their integration proposals for AI Command Center.  
**Patterns reviewed:** PAT-001, PAT-003, PAT-004, PAT-006, PAT-007.  
**Integration proposals reviewed:** INT-001, INT-005, INT-007.  
**Superseded:** INT-003 and INT-004 are stale from an earlier pattern numbering pass and are replaced by ADR-008 and ADR-009.

**Reference authority:** `PROJECT_CONSTITUTION_V4.md`, `AGENTS.md`, `ARCHITECTURE.md`, `ARCHITECTURE_ENFORCEMENT.md`, `docs/architecture/AGENT_RUNTIME_INTERFACE.md`, `docs/architecture/MODEL_ORCHESTRATION.md`, `docs/architecture/CHAT_MODERNIZATION_SPEC.md`, `docs/architecture/ADR-004_RUNTIME_APPROVAL_MODEL.md`, `docs/architecture/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`.

---

## Executive Summary

The five promoted patterns from `block/goose` fit ACC's state-driven, EventBus-governed architecture. Each proposal routes state through `AppState`, avoids global modules and direct service-to-service calls, and preserves the ownership chain `UI → AppState → EventBus → Services → Repositories → Storage`. The patterns are additive and do not replace existing primitives. Risks are identified and mitigated. Approved for ADR drafting.

---

## Verdict

| Check | Result |
|-------|--------|
| Constitution Compliance | **PASS** |
| Architecture Compliance | **PASS** |
| AppState Compliance | **PASS** |
| Primitive Reuse Compliance | **PASS** |
| CustomTkinter Compliance | **PASS** (no UI framework changes proposed) |
| Overall | **APPROVED FOR ADR** |

---

## Per-pattern findings

### PAT-001 — Declarative Provider Registry with Inventory State

- **Evidence:** `research/patterns/PAT-001.md`, `research/integration/INT-001.md`, `docs/architecture/MODEL_ORCHESTRATION.md`, `docs/architecture/AGENT_RUNTIME_INTERFACE.md`.
- **Finding:** A read-only provider catalog in `AppState` is consistent with existing `ModelRouterService` and `AgentRuntimeProvider` contracts. The registry provides metadata and configuration-key discovery; it does not execute model calls.
- **Risk:** Registry could become a second source of truth for active provider selection.
- **Mitigation:** `ModelRouterService` remains the execution authority; the registry only publishes `provider.discovered` / `provider.configured` snapshots for UI/model picker.

### PAT-003 — Conversation Context Compaction with Visibility Metadata

- **Evidence:** `research/patterns/PAT-003.md`, `docs/architecture/CHAT_MODERNIZATION_SPEC.md`.
- **Finding:** Compaction preserves user-visible history while giving the model a summarized context. Aligns with chat-as-tool and workspace-attached chat goals.
- **Risk:** Summarization quality depends on a fast model and token counter.
- **Mitigation:** Make compaction triggered by an explicit `context.over_budget` event; preserve the most recent user message; keep original messages in repository with visibility flags.

### PAT-004 — Tool Inspector / Confirmation Router Pipeline

- **Evidence:** `research/patterns/PAT-004.md`, `docs/architecture/ADR-004_RUNTIME_APPROVAL_MODEL.md`, `docs/architecture/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`.
- **Finding:** A confirmation router that emits `action_required` and waits for user approval strengthens the existing runtime approval model without bypassing `ToolExecutorService`.
- **Risk:** Could duplicate `PermissionService` checks.
- **Mitigation:** Integrate with existing `CommandSandbox` and `PermissionService`; treat inspectors as an advisory layer that can escalate to `action_required`.

### PAT-006 — Modular Tool Inspection and Permission Pipeline

- **Evidence:** `research/patterns/PAT-006.md`, `research/integration/INT-005.md`, `docs/architecture/ADR-004_RUNTIME_APPROVAL_MODEL.md`.
- **Finding:** Pluggable security, egress, adversary, and repetition inspectors are a clean extension of `ToolExecutorService`. The pattern uses `EventBus` for findings and `action_required` events, preserving state authority.
- **Risk:** Adversary inspector is LLM-based and slow; false positives can frustrate users.
- **Mitigation:** Adversary inspector is opt-in; inspectors can be ordered and disabled via settings; `AlwaysAllow` is revocable.

### PAT-007 — Layered Telemetry with Pluggable Backends

- **Evidence:** `research/patterns/PAT-007.md`, `research/integration/INT-007.md`, `AGENTS.md` telemetry requirements.
- **Finding:** Adding exporter plugins behind `TelemetryService` extends the existing `telemetry.event` stream without introducing new global sinks.
- **Risk:** External backends can leak PII or block on network.
- **Mitigation:** Exporters run in an async queue with independent failure isolation; PII scrubbing is required before any third-party backend.

---

## Deficiencies

- **D-01:** `research/integration/INT-003.md` and `research/integration/INT-004.md` still contain pre-rename content for session locks and cancellation tokens. They are superseded by ADR-008 and ADR-009 and should be marked `Superseded`.
- **D-02:** PAT-001 must define how it composes with `AGENT_RUNTIME_INTERFACE.md` provider contract; the ADR must include a concrete `ProviderRegistrySnapshot` schema.
- **D-03:** PAT-003 must specify the token counter source and the summarization model selection policy before implementation.

---

## Risk Assessment

| Pattern | Short-Term Risk | Long-Term Risk |
|---------|-----------------|----------------|
| PAT-001 | Low | Low if registry stays read-only |
| PAT-003 | Medium (tokenizer/summarizer integration) | Low |
| PAT-004 | Medium (UX friction) | Low |
| PAT-006 | Medium (false positives, latency) | Low |
| PAT-007 | Low | Low for console/JSON; medium for external backends |

---

## Next Actions

1. Draft ADRs:
   - ADR-007 — Provider Registry Snapshot in AppState (PAT-001)
   - ADR-008 — Conversation Context Compaction with Visibility Metadata (PAT-003)
   - ADR-009 — Tool Confirmation Router Pipeline (PAT-004)
   - ADR-010 — Modular Tool Inspection and Permission Pipeline (PAT-006)
   - ADR-011 — Layered Telemetry Backends (PAT-007)
2. Update `research/patterns/index.md` ADR column and pattern cards.
3. Mark `INT-003.md` and `INT-004.md` as superseded.
4. Implementation planning after ADR acceptance.
