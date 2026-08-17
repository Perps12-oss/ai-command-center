# Constitutional Pre-Flight — Gate 5 Windows ARM64 GUI operator attestation

**Date:** 2026-08-17  
**Authority:** Article X; `docs/governance/STRATEGIC_RUNTIME_PROGRAM.md` Gate 5; `docs/governance/IMPLEMENTATION_GUIDE.md` Queue 1; `docs/governance/PHASE_COMPLETION_RULE.md`.  
**Implementation start:** blocked until this file exists. This change is **documentation of operator-attested GUI runtime**, not Stream code.

## What this change is

Record the operator statement that the Windows ARM64 desktop GUI is working and verified. Linux Cloud cannot launch `main.py` (`is_arm64()` false). The Linux keyword/governance ledger remains `docs/audits/GATE5_LINUX_VERIFICATION.md`.

## What this change is not

- Not Wave 5 full-system soak (Intent → … → explanation).
- Not EventBus isolation / ADR-026.
- Not Stream G Cross-OS.
- Not a claim that this Cloud agent executed the GUI.
- Not phase-complete until the attestation and Linux ledger exist on `main`.

## Invariants

No new EventBus topics, services, or ADRs. Operator attestation is Class B relative to machine logs; Linux pytest/arch_lint/UCGS remain Class A for those hosts.
