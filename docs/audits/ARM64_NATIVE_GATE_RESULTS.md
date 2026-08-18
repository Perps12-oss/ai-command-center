# ARM64 Native Gate — results

**Workflow:** `.github/workflows/arm64-gate.yml`  
**Runner:** `windows-11-arm` (not `windows-latest`)  
**Python in CI:** 3.12 `architecture: arm64`  
**ISA ledger:** [`ARM64_ISA_EVIDENCE_2026-08-16.md`](ARM64_ISA_EVIDENCE_2026-08-16.md)

## Enablement

PR/push triggers are **on**. The job runs:

1. Confirm `platform.machine() == ARM64`
2. Two-tier `scripts/check_arm64_binaries.py --json`
3. Full pytest (including `@arm64` when native)

`scripts/preflight_arm64.py` is **not** in CI: it hard-fails when Ollama HTTP is down, which is service availability, not ISA.

## First successful run

Recorded when GitHub Actions completes `windows-11-arm` for this close-out PR. Until that job is green, this file is **enablement only**, not a Class A PE proof. Operator 2026-08-16 remains the desktop ISA ledger.
