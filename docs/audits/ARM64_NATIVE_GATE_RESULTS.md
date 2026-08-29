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

| Field | Value |
|-------|--------|
| Date | 2026-08-19 |
| Runner | `windows-11-arm` |
| Python | 3.12.10 arm64 (`platform.machine()==ARM64`) |
| Result | **pass** |
| Example | [run 32199598840](https://github.com/Perps12-oss/ai-command-center/actions/runs/32199598840) (7m34s) on tip `1f8205d` |

Operator 2026-08-16 remains the desktop ISA ledger (Python 3.14). CI proves native ARM64 3.12 + two-tier PE scan + pytest.
