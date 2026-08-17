# Wave 4 — Gate 5 verification (ADR-025 Adapt F1–F4)

**Date:** 2026-08-17  
**Program:** Strategic Runtime Program Wave 4 / Stream F  
**Authority:** ADR-025 §9 (“After Gate 4: Gate 5 = Linux + Windows verification”)  
**Code under test:** branch `cursor/gate4-stream-f-adapt-f1-f4-6031` @ `883e7c0` (Gate 4 F1–F4)  
**Pre-flight:** `docs/audits/PREFLIGHT_WAVE4_GATE5_GATE6.md`

**Verdict: PASS** — Linux machine checks green; Windows ARM64 runtime enforcement operator-attested.

## Operator attestation (Windows ARM64)

Operator reported 2026-08-17:

- F1–F4 runtime enforcement verified
- Provider allowlist works
- Cancel + creation lock behave correctly
- Runs ledger stays bounded (≤64)

This Cloud host cannot launch `main.py` (x86_64). Windows evidence is Class B operator attestation.

## Linux (Class A) — Cursor Cloud x86_64 / Python 3.12.3

| Check | Result |
|-------|--------|
| `pytest` `test_architecture_lint` + `test_orchestrator_run_cancel` + `test_receipt_boundary` + `test_execution_orchestrator_service` | **49 passed** |
| `arch_lint.py --baseline tests/arch_lint_baseline.json` | **OK** (4 baselined) |
| `verify_constitution.py` | **PASS** |
| `ucgs_runner` + `ucgs_ci_gate` | **`[UCGS PASS]`** S1 |
| `create_application()` startup/shutdown | printed **OK** |

## F\* acceptance mapping

| ID | Claim | Evidence |
|----|-------|----------|
| F1 | Package boundary R6/R7 enforced | arch_lint unit tests + repo ratchet |
| F2 | Provider allowlist R8 works | arch_lint R8 tests; operator attestation; `provider_sdk` unwired |
| F3 | Cancel + creation lock correct | `test_orchestrator_run_cancel.py`; operator attestation |
| F4 | Runs ledger bounded ≤64 | `_MAX_ACTIVE_RUNS = 64`; eviction test; operator attestation |

## Gate 5 exit

Both environments pass → this file is the Gate 5 ledger. Gate 6 = merge Gate 4 code + this ledger (+ close-out) to `main`.
