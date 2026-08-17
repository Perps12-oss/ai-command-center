# Goose Pattern Adoption Record

**Status:** Gate 2 CLOSED 2026-08-14. Gate 3 §9 on `main`. Gate 4 Adapt F1–F4 **implemented** on this branch (merge to `main` completes Gate 4).
**Authority:** [`ADR-025_GOOSE_PATTERN_ADOPTION.md`](../adr/ADR-025_GOOSE_PATTERN_ADOPTION.md) — **Accepted** (§9 Gate 3 plan)
**Proposal:** [IP_F_GOOSE_PATTERN_ADOPTION.md](IP_F_GOOSE_PATTERN_ADOPTION.md)

Map each pattern:

`Goose pattern → ACC equivalent → decision (Adopt/Adapt/Reject) → implementation → verification`

| Goose pattern | ACC equivalent | Decision | Implementation | Verification |
|---------------|----------------|----------|----------------|--------------|
| Provider-types crate split | `runtime/` + domain contracts | **Adapt** | ADR-025 §9 **F2** — arch_lint R8 allowlist + ARI ownership row; `provider_sdk` unwired | `tests/test_architecture_lint.py` R8 + composition-root scan |
| Package/crate boundary discipline | `scripts/arch_lint.py` | **Adapt** | ADR-025 §9 **F1** — arch_lint R6/R7 | `tests/test_architecture_lint.py` R6/R7; repo ratchet green |
| Per-session cancellation / creation locks | run_id cancellation on orchestrator | **Adapt** | ADR-025 §9 **F3** — filled gaps: `EXECUTION_RUN_CANCEL` + creation lock ([`ADR025_F3_CANCEL_COVERAGE.md`](../../audits/ADR025_F3_CANCEL_COVERAGE.md)) | `tests/test_orchestrator_run_cancel.py` |
| Bounded LRU actor cache | AppState / service caches | **Adapt**, bounds mandatory | ADR-025 §9 **F4** — `ExecutionOrchestratorService._runs` OrderedDict + `_MAX_ACTIVE_RUNS` | `tests/test_orchestrator_run_cancel.py` eviction cases |
| Electron desktop / Goose Serve | ACC Tk UI + host OS | **Reject** | N/A | N/A |
| Global config / OnceCell managers | Forbidden globals | **Reject** | N/A | N/A |
| Agent loop as product identity | ExecutionAuthority pipeline | **Reject** | N/A | N/A |
| MCP bundled as SoT | ExternalCapabilityBridge as capability | **Reject** | N/A | N/A |

**Wave 4 order:** F1 → F2 → F3 → F4 (complete in this Gate 4 PR). **Reject** rows remain closed.
