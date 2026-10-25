# Constitutional Pre-Flight — ARM64 two-tier close-out (v1.0 package)

**Date:** 2026-08-18  
**Authority:** Article X; owner ISA statement 2026-08-16; [`ARM64_PLATFORM_CONTRACT_REMEDIATION_PLAN.md`](ARM64_PLATFORM_CONTRACT_REMEDIATION_PLAN.md) sequence step 4.  
**Baseline:** branch `cursor/multi-arch-windows-feasibility-audit-9f49` on top of `origin/main` @ `354681b`.

## What this change is

Align scanner, wheel_audit, matrix, and docs on a **locked two-tier** Windows ARM64 contract: core (process + Ollama + inference-critical) native `0xAA64`; named utility allowlist may be AMD64. Record operator ISA evidence from 2026-08-16. Enable `arm64-gate.yml` on PR/push using existing `windows-11-arm` (not x64 `windows-latest`).

## What this change is not

- Not x86-64 SKU, ADR-026, Stream G, or a PERF Art XV Closed claim.
- Not adding `preflight_arm64.py` to CI (Ollama HTTP would fail closed on runners without the service).
- Not tagging `v1.0` on a feature branch; phase-complete / release tag only after merge to `main`.
- Not inventing PE hex dumps beyond the operator fields provided in the close-out delegation.

## Invariants

No EventBus/topic changes, no UI storage access, no service-to-service calls. Scanner FAIL remains for **non-allowlisted** AMD64 PE. `validate_ollama_arm64_native()` stays ARM64-only.
