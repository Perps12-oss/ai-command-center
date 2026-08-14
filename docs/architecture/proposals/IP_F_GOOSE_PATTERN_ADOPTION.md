# IP-F — Goose pattern adoption (selective)

**Status:** GATE 1 DRAFT — awaiting owner Gate 2  
**Stream:** F  
**Parent ADR:** none. Research only until Gate 2.  
**Research:** [`legacy_goose_expedition_report.md`](../../../research/repositories/exp-001-goose/notes/legacy_goose_expedition_report.md)  
**Baseline:** [STRATEGIC_GAP_MATRIX.md](../../audits/STRATEGIC_GAP_MATRIX.md) Stream F

---

1. **Problem.** Identify Goose (and similar) **patterns** that strengthen ACC without becoming Goose-compatible or displacing ACC authorities.

2. **Exists.** ACC layering, EventBus, provider HTTP adapters, arch_lint, ARI. Expedition already classified many subsystems Adopt/Adapt/Ignore. **No Goose code in ACC runtime.**

3. **Owning boundary.** Architecture/docs + targeted ACC modules. Goose remains an external reference repository, never SoT.

4. **Remain authoritative.** Workspace State, canonical runtime, ExecutionAuthority, TruthBoundary, receipts, governance, privacy, PERFORMANCE_CONSTITUTION.

5. **New behavior.** Produce and execute a **Goose Pattern Adoption Record** (Adopt / Adapt / Reject). Implementation only for Adopt/Adapt rows after Gate 3.

6. **Rejected as objectives.** Goose compatibility; embedding Goose UI; Goose session/memory as ACC memory; global `Config::global()`-style state; CoT/logprob autonomy copied from Goose UX.

7. **Dependencies.** Prefer after A–C contracts are stable (dependency graph). Queue 2 items (provider abstraction, plugins, logging, desktop) are **inputs to this IP**, not separate Queue 1 tickets.

8. **Invariants.** Inv 13; Rule 2 no globals; Rule 3 EventBus; ARI.

9. **Tests.** Per adopted pattern (arch-lint import rules, cancellation tests, etc.). No Goose e2e.

10. **Invalid if.** `provider_sdk` live-wire that shadows AppState; third-party console; ACC persistence replaced by Goose sessions.

### Preliminary categories (evidence for Gate 2 — not yet decided)

| Goose pattern | ACC equivalent | Preliminary |
|---------------|----------------|-------------|
| Provider-types crate split | `runtime/` + domain contracts | Adapt |
| Package/crate boundary discipline | `arch_lint.py` | Adapt |
| Per-session cancellation / creation locks | run_id cancellation on orchestrator | Adapt (if missing) |
| Bounded LRU actor cache | AppState / service caches | Adapt only with bounds |
| Electron desktop / Goose Serve | ACC Tk UI + host OS | Reject |
| Global config / OnceCell managers | Forbidden globals | Reject |
| Agent loop as product identity | ExecutionAuthority pipeline | Reject |
| MCP bundled as SoT | ExternalCapabilityBridge as capability | Adapt/Reject per ADR |

**Gate 2 ask:** ACCEPT the Adopt/Adapt/Reject table (edit as needed) as ADR-024+ **or** REJECT Goose track with condition “research archive only.”

Close-out file: [GOOSE_PATTERN_ADOPTION_RECORD.md](GOOSE_PATTERN_ADOPTION_RECORD.md).
