# Constitutional Pre-Flight — ARM64 ISA evidence capture (sequence steps 2–3)

**Date:** 2026-08-18  
**Authority:** Article X; owner-locked [`ARM64_PLATFORM_CONTRACT_REMEDIATION_PLAN.md`](ARM64_PLATFORM_CONTRACT_REMEDIATION_PLAN.md); Outcome C [`MULTI_ARCHITECTURE_FEASIBILITY_AUDIT.md`](MULTI_ARCHITECTURE_FEASIBILITY_AUDIT.md).  
**Implementation start:** capture tooling + ledgers only. Scanner / matrix / `main.py` policy **unchanged**.

## What this change is

Sequence **steps 2–3**: a machine-readable capture script and operator session protocol so host ISA, Python PE, Ollama PE, scanner JSON, preflight, git SHA, and §4.1 allowlist **candidates** can be recorded. Allowlist policy remains **pending**; matrix WARN is not a grant.

## What this change is not

- Not x86-64 SKU work, ADR-026, Stream G, or v1.0/v1.1 scope.
- Not sequence step 4 (reconcile scanner/matrix/tests).
- Not granting aiohttp / watchdog / pywin32 exceptions.
- Not PERF Art XV closeout.
- Not claiming this Cloud Linux host is a native ARM64 release environment.
- Not a substitute for the operator Windows ARM64 session.

## Invariants

UI isolation, no new EventBus topics, no service-to-service calls, no global state. Capture reads existing `detector.py` / `wheel_audit.py` / `check_arm64_binaries.py` and does not weaken PE FAIL rules.
