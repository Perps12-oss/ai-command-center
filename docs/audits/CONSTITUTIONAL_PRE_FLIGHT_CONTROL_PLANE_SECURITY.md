# Constitutional Pre-Flight — Control-Plane Security Audit

**Date:** 2026-08-12  
**Baseline:** `origin/main` @ `1ee05ba` (post fossil cleanup #173)  
**Branch:** `cursor/control-plane-security-audit-4b28`  
**Authority:** `PROJECT_CONSTITUTION_V4.md`; ADR-004, ADR-009, ADR-018; Inv 4 (no service→service), Inv 9 (telemetry), Inv 12 (non-circumvention)

---

## Scope

**In scope:** Read-only security audit (A–C) + **adversarial acceptance tests** encoding control-plane invariants **before** remediation.

**Out of scope (this PR):** Changing `auto_approve`, actor identity stamping, sandbox allowlists, or production approval logic. Tests are expected to **fail** on current `main` until a follow-up fix PR.

---

## Article X

This pre-flight authorizes audit documentation and failing acceptance tests only. No runtime behavior change in this branch.

---

## Hard stops checked

| Condition | Result |
|-----------|--------|
| Fix required to write tests | **No** — tests assert desired invariants against current wiring. |
| Accepted ADR conflicts with live path | **ADR-004 / ADR-009 intent** conflicts with `auto_approve=True` on EA intake — reported, not silently fixed here. |
| TruthBoundary owns approval | **No** — TruthBoundary validates post-execution narrative only. |

---

## Decision

Proceed with audit report + `tests/test_control_plane_security_acceptance.py` (expected failures on `main`).
