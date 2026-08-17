# Constitutional Pre-Flight — Wave 4 Gate 4 ADR-025 Adapt F1–F4

**Date:** 2026-08-17  
**Authority:** Article X; Accepted [`ADR-025_GOOSE_PATTERN_ADOPTION.md`](../architecture/adr/ADR-025_GOOSE_PATTERN_ADOPTION.md) §9; Inv 13 / Rule 2 / Rule 3; `PHASE_COMPLETION_RULE.md`.  
**Baseline:** `origin/main` @ Gate 3 §9 merge (`50c08eb` line).  
**Implementation start:** blocked until this file exists.

## What this change is

Gate 4 product code for Stream F Adapt rows, **only** as specified in ADR-025 §9:

| ID | Work |
|----|------|
| F1 | Extend `scripts/arch_lint.py` with package-boundary rules (runtime↛ui/services, domain↛ui/services) + tests |
| F2 | Enforce concrete `runtime.providers` import discipline via lint allowlist; ARI ownership note; `provider_sdk` unwired proof |
| F3 | Verify cancel coverage; fill orchestrator run cancel + creation lock via EventBus |
| F4 | Bound `ExecutionOrchestratorService._runs` with explicit LRU max |

## What this change is not

- Goose code import / Electron / globals / MCP-as-SoT
- Stream D isolation, Stream E embeddings, Stream G
- Wave 4 Gate 5/6 close-out (verification ledger after this lands)

## Invariants

Pattern adoption only. No OnceCell cancel maps. New topic only if orchestrator cancel cannot reuse LLM/agent/goal cancel (expected: `execution.run.cancel`). Composition root remains sole live-wire path; `provider_sdk` stays dormant.
