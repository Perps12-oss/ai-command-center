# Architecture Decision Records (ADR) Index

**Authority:** ADRs are **subordinate** to `PROJECT_CONSTITUTION_V4.md`. They do **not** occupy Article II Level 2 (that slot is `AGENTS.md` and `docs/ARCHITECTURE_ENFORCEMENT.md`).  
**Binding rule:** **Accepted** ADRs are binding architectural decisions under V4 — implementers must follow them. **Proposed** ADRs are **non-binding**. Neither status amends V4 unless Article XIV is followed.  
**Process:** Major architecture decisions use [`ARCHITECTURE_DECISION_FRAMEWORK.md`](../../governance/ARCHITECTURE_DECISION_FRAMEWORK.md) (multi-council review).  
**Location:** This directory. Naming: `ADR-NNN_UPPER_SNAKE_CASE.md`.

---

## Status legend

| Status | Meaning |
|--------|---------|
| Proposed | **Non-binding** — binding intent undecided or not yet Accepted |
| Accepted | **Binding** under V4; implementers must follow (not a constitutional Level 2 identity) |
| Accepted — disposition | Accepted with retire / research-only / remain-outside outcome |
| Narrowed by | Later Accepted ADR constrains scope without full supersession |

---

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [001](ADR-001_PERSISTENCE_STRATEGY.md) | Persistence Strategy | Proposed |
| [002](ADR-002_SCHEDULER_MODEL.md) | Scheduler Model | Proposed |
| [003](ADR-003_OBSERVER_FLOW.md) | Observer Flow | Proposed |
| [004](ADR-004_RUNTIME_APPROVAL_MODEL.md) | Runtime Approval Model | Proposed |
| [005](ADR-005_WORLD_MODEL_AUTHORITY.md) | World Model Authority | Proposed |
| [006](ADR-006_EXECUTION_AUTHORITY_CANONICAL.md) | Execution Authority Canonical | Accepted |
| [007a](ADR-007_APPSTATE_NOTIFICATION_STORMS.md) | AppState Notification Storms | Accepted |
| [007b](ADR-007_PROVIDER_REGISTRY.md) | Provider Registry | Proposed |
| [008](ADR-008_CONVERSATION_COMPACTION.md) | Conversation Compaction | Proposed — **narrowed by ADR-020** |
| [009](ADR-009_TOOL_CONFIRMATION_ROUTER.md) | Tool Confirmation Router | Proposed — **narrowed by ADR-018** |
| [010](ADR-010_MODULAR_TOOL_INSPECTION.md) | Modular Tool Inspection | Proposed |
| [011](ADR-011_TELEMETRY_BACKENDS.md) | Telemetry Backends | Proposed |
| [012](ADR-012_GOALS_PHASE9_DISPOSITION.md) | Goals Phase 9 Disposition | Accepted — retire GoalEngine |
| [013](ADR-013_PLANNING_AGENT_COORDINATOR_DISPOSITION.md) | Planning / AgentCoordinator Disposition | Accepted — research-only |
| [014](ADR-014_PREDICTIVE_UNDO_DISPOSITION.md) | Predictive Undo Disposition | Accepted — research-only |
| [015](ADR-015_STATE_AUTHORITY_MUTATE_MEMORY.md) | SA Mutate Memory | Accepted |
| [016](ADR-016_STATE_AUTHORITY_MUTATE_GOALS.md) | SA Mutate Goals | Accepted |
| [017](ADR-017_SA_MUTATE_WORKFLOWS_EXECUTIONS_AGENTS_DISPOSITION.md) | SA Mutate WEA Disposition | Accepted — remain outside |
| [018](ADR-018_TOOL_INVOCATION_ARCHITECTURE.md) | Tool Invocation Architecture | Accepted — Hybrid B-primary |
| [019](ADR-019_PLANNING_ARCHITECTURE.md) | Planning Architecture | Accepted — B with explicit replan |
| [020](ADR-020_MEMORY_ARCHITECTURE.md) | Memory Architecture | Accepted — World Model canonical |
| [021](ADR-021_EXPLAINABILITY.md) | Explainability | Accepted — Decision Records |
| [022](ADR-022_CONFIDENCE_AND_AUTONOMY.md) | Confidence & Autonomy | Accepted — composite confidence |
| [023](ADR-023_MODEL_STRATEGY.md) | Model Strategy | Accepted — brain-independent |

### Section 9 implementation notes

- Intention contract: [`docs/architecture/INTENTION_CONTRACT.md`](../INTENTION_CONTRACT.md)
- Memory boundary: [`docs/architecture/MEMORY_BOUNDARY.md`](../MEMORY_BOUNDARY.md)
- Degrade modes: [`docs/architecture/MODEL_ORCHESTRATION.md`](../MODEL_ORCHESTRATION.md)
- Pre-flight: [`docs/audits/CONSTITUTIONAL_PRE_FLIGHT_SECTION9_FOLLOWONS.md`](../../audits/CONSTITUTIONAL_PRE_FLIGHT_SECTION9_FOLLOWONS.md)

### Number collision (permanent labels)

**ADR-007** was assigned twice historically (`APPSTATE_NOTIFICATION_STORMS` = **007a**, `PROVIDER_REGISTRY` = **007b**). **Do not renumber.** Keep **007a** / **007b** permanently. Prefer explicit filenames; treat 007a/007b as stable index labels only.

### Next free number

**ADR-024**.

---

## Council-format series (018–023)

These ADRs used the permanent multi-council framework. Informal roadmap labels “ADR-001 Tool Invocation” … “ADR-006 Model Strategy” map here as **018–023**, not to the historical 001–006 files.
