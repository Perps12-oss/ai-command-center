# v1.0 close-out ledger — Windows ARM64 two-tier

**Package date:** 2026-08-18  
**SKU:** Windows ARM64 desktop (native Python + native Ollama)  
**Rule:** [`PHASE_COMPLETION_RULE.md`](../governance/PHASE_COMPLETION_RULE.md) — **COMPLETE only after this package is on `main`**. Do not treat a feature-branch tip as the release.

**ISA:** [`ARM64_ISA_EVIDENCE_2026-08-16.md`](ARM64_ISA_EVIDENCE_2026-08-16.md)  
**Contract:** [`../PLATFORM_CONTRACT.md`](../PLATFORM_CONTRACT.md)

## Proof recorded

- [x] Host: Windows ARM64 (operator 2026-08-16)
- [x] Python: native ARM64 (`pythoncore-3.14-64`, `platform.machine()==ARM64`)
- [x] Ollama: native ARM64 PE `0xAA64` (operator)
- [x] Preflight: Phase 0 PASS (operator)
- [x] Two-tier policy encoded in `arm64_policy.py` (scanner + wheel_audit + matrix)
- [x] `arm64-gate.yml` enabled on PR/push (`windows-11-arm`)
- [ ] `arm64-gate` first green run — fill when Actions completes
- [ ] `v1.0` git tag — only on `main` after merge

## Explicitly not claimed

- PERF Art XV **Closed** (still Mitigated; soak operator-owned)
- Windows x86-64 SKU
- Stream G Cross-OS
- Stream D EventBus isolation

## Deferred

- x86-64: reopen [`MULTI_ARCHITECTURE_FEASIBILITY_AUDIT.md`](MULTI_ARCHITECTURE_FEASIBILITY_AUDIT.md) only after this package is on `main` and arm64-gate has a successful run
- macOS/Linux GUI: Stream G
- Stream D isolation: still gated on measurement + ADR if needed (do not assume ADR-026)
- Stream E embeddings: still deferred (not “Wave 4”)

## Authorization

ISA + two-tier **alignment** is the close-out package. **v1.0 tag / “complete”** requires merge to `main` (and tag) by the owner. This file is not a substitute for that merge.
