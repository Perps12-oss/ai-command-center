# Goose Pattern Adoption Record

**Status:** Gate 2 CLOSED 2026-08-14 — decision column Accepted. Gate 3 §9 (F1–F4) written on ADR-025 — **Gate 4 code not started**.
**Authority:** [`ADR-025_GOOSE_PATTERN_ADOPTION.md`](../adr/ADR-025_GOOSE_PATTERN_ADOPTION.md) — **Accepted** (§9 Gate 3 plan)
**Proposal:** [IP_F_GOOSE_PATTERN_ADOPTION.md](IP_F_GOOSE_PATTERN_ADOPTION.md)

Map each pattern:

`Goose pattern → ACC equivalent → decision (Adopt/Adapt/Reject) → implementation → verification`

| Goose pattern | ACC equivalent | Decision | Implementation | Verification |
|---------------|----------------|----------|----------------|--------------|
| Provider-types crate split | `runtime/` + domain contracts | **Adapt** | Gate 3 ready — ADR-025 §9 **F2**; Gate 4 not started | — |
| Package/crate boundary discipline | `scripts/arch_lint.py` | **Adapt** | Gate 3 ready — ADR-025 §9 **F1**; Gate 4 not started | — |
| Per-session cancellation / creation locks | run_id cancellation on orchestrator | **Adapt** (if missing — verify current coverage first) | Gate 3 ready — ADR-025 §9 **F3**; Gate 4 not started | — |
| Bounded LRU actor cache | AppState / service caches | **Adapt**, bounds mandatory | Gate 3 ready — ADR-025 §9 **F4**; Gate 4 not started | — |
| Electron desktop / Goose Serve | ACC Tk UI + host OS | **Reject** | N/A | N/A |
| Global config / OnceCell managers | Forbidden globals | **Reject** | N/A | N/A |
| Agent loop as product identity | ExecutionAuthority pipeline | **Reject** | N/A | N/A |
| MCP bundled as SoT | ExternalCapabilityBridge as capability | **Reject** | N/A | N/A |

**Wave 4 order:** F1 → F2 → F3 → F4 (see ADR-025 §8). **Reject** rows are closed — do not reopen without a superseding ADR. Fill Verification at Gate 4/5.
