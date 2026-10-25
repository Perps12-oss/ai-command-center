# Wave 4 — Close-out (Gate 6)

**Date:** 2026-08-17  
**Program wave:** Wave 4 — External pattern hardening (Goose Adapt F1–F4)  
**Authority:** ADR-025 §9 Gate 4 exit + Gate 5/6; `PHASE_COMPLETION_RULE.md`  
**Pre-flight:** `docs/audits/PREFLIGHT_WAVE4_GATE5_GATE6.md`  
**Gate 5 ledger:** `docs/audits/WAVE_4_GATE_5_VERIFICATION.md`

**Status on this branch tip:** close-out package ready with Gate 4 Adapt code.  
**Status on `origin/main`:** **Wave 4 COMPLETE** only after this package (Gate 4 code + Gate 5 ledger + this file) is merged.

## Delivered on merge

| Gate | Artifact |
|------|----------|
| 3 | ADR-025 §9 on `main` (#196) |
| 4 | Adapt F1–F4 code (`arch_lint` R6–R8, `EXECUTION_RUN_CANCEL`, creation lock, bounded `_runs`) |
| 5 | `WAVE_4_GATE_5_VERIFICATION.md` — Linux PASS + Windows operator attestation |
| 6 | This close-out |

## Unblocks

**Wave 6 / Stream G (Cross-OS)** planning is **unblocked**. This does **not** auto-start Cross-OS product code — Stream G still requires its own Gate 1–3 pipeline before implementation.

## Still gated (not Wave 4)

| Item | Status |
|------|--------|
| Stream D isolation | Not unlocked |
| Stream E embeddings | Deferred |
| Stream G implementation | Unblocked to **open**, not started |

## Invalid claims

- Declaring Wave 4 complete before this package is on `main`
- Starting Stream G code without Stream G Gate 1–3
- Treating Goose Adapt as Goose compatibility
