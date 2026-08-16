# Goose Pattern Adoption Record

**Status:** Gate 2 CLOSED 2026-08-14 — decision column below is Accepted. Implementation/Verification columns fill in per-row at Wave 4, each behind its own Gate 3 Section 9 plan.
**Authority:** [`ADR-025_GOOSE_PATTERN_ADOPTION.md`](../adr/ADR-025_GOOSE_PATTERN_ADOPTION.md) — **Accepted**
**Proposal:** [IP_F_GOOSE_PATTERN_ADOPTION.md](IP_F_GOOSE_PATTERN_ADOPTION.md)

Map each pattern:

`Goose pattern → ACC equivalent → decision (Adopt/Adapt/Reject) → implementation → verification`

| Goose pattern | ACC equivalent | Decision | Implementation | Verification |
|---------------|----------------|----------|----------------|--------------|
| Provider-types crate split | `runtime/` + domain contracts | **Adapt** | Not started — Wave 4, own Gate 3 plan | — |
| Package/crate boundary discipline | `scripts/arch_lint.py` | **Adapt** | Not started — Wave 4, own Gate 3 plan | — |
| Per-session cancellation / creation locks | run_id cancellation on orchestrator | **Adapt** (if missing — verify current coverage first) | Not started — Wave 4, own Gate 3 plan | — |
| Bounded LRU actor cache | AppState / service caches | **Adapt**, bounds mandatory | Not started — Wave 4, own Gate 3 plan | — |
| Electron desktop / Goose Serve | ACC Tk UI + host OS | **Reject** | N/A | N/A |
| Global config / OnceCell managers | Forbidden globals | **Reject** | N/A | N/A |
| Agent loop as product identity | ExecutionAuthority pipeline | **Reject** | N/A | N/A |
| MCP bundled as SoT | ExternalCapabilityBridge as capability | **Reject** | N/A | N/A |

This table is now Queue 1 for its **Adapt** rows, gated behind Wave 4 and their individual Gate 3 Section 9 plans (per `ADR-025_GOOSE_PATTERN_ADOPTION.md` §3). **Reject** rows are closed — do not reopen without a superseding ADR.
