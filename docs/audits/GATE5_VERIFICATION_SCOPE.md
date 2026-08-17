# Gate 5 — Verification Scope (Streams A, B, C, E-M1, B5)

**Date:** 2026-08-16  
**Program gate:** Gate 5 = tests + runtime + architecture + governance evidence  
**Not:** Wave 5 full-system soak (Intent → … → explanation) — that is a later wave.  
**Not:** Deployment, packaging, or store release — **undefined** in Queue 1; do not invent.

**Rule:** Gate 5 is **not complete** until this evidence is on `main` (`PHASE_COMPLETION_RULE.md`). This file is a **scope**, not a close-out.

## What Gate 4 already put on `main`

| Stream | Gate 4 code | Local/CI keyword |
|--------|-------------|------------------|
| A ADR-021 | Ordinary-path Decision Records, `__missing__`, DecisionCard conditional | `-k decision_record` |
| B ADR-022 | §11 bands, escalate-only | `-k autonomy_escalation` |
| C ADR-023 | M2 already live; M3 local-only replan/destroy; M4 telemetry reason | `-k model_degradation or tier_pooling or orchestration` |
| E ADR-024 M1 | Read-only `FederationService` wired | `-k federation_m1` |
| B5 ADR-006 §12 | Hero `UI_COMMAND` path (product from #168) | `-k goal_intake_hero` |

Combined selectors: 28 passed on `main` @ `f35cb98` (2026-08-16).

## Gate 5 evidence matrix

| Level | Work | Host | Status |
|-------|------|------|--------|
| Tests | Keywords above + orchestrator/receipt regression | Linux CI + Windows CI | **Partial** — pytest jobs went green on the Gate 4 PRs; keep them green on `main` |
| Architecture | `arch_lint.py --baseline`; no new service→service; no invented topics | Linux | Required on every Gate 5 PR |
| Governance | `verify_constitution.py`; `ucgs_runner` + `ucgs_ci_gate` | Linux | Required |
| Runtime headless | `create_application()` + `startup()`; federation READY; EA intake | Linux `APPDATA` | Covered in factory/intake tests |
| Runtime GUI | DecisionCard / Brain Reasoning / Hero New Goal | **Windows ARM64 only** | **Open** — Cloud Linux cannot launch `main.py` |
| UI Constitution | `scripts/verify_ui_constitution.py` | Linux (static) | Separate from Gate 4; do not conflate remaining chrome FAIL with these streams |
| Full-system Wave 5 | Intent → routing → EA → execute → TruthBoundary → receipt → AppState → timeline → Decision Record | Windows ARM64 + headless | **Not this gate** |

## Out of scope (do not treat as Gate 5)

- Stream D isolation / pools (blocked; see Stage 1 report)
- Stream E vectors / embeddings (ADR-024 condition; UCGS `scope_embeddings` S5)
- Stream F Goose Adapt (Wave 4)
- Stream G Cross-OS
- App deployment, installers, ARM64 packaging beyond existing product constraints
- Generic “UI hardening” unrelated to DecisionCard / Hero / Brain bindings already specified in ADR-021 §12 M3/M5

## Suggested Gate 5 PRs (docs/tests only unless a defect is found)

1. **Verification ledger** — this file on `main` plus a checklist run attached to a PR (constitution, ucgs, arch_lint, keyword pytest).  
2. **Windows ARM64 operator note** — screenshots/recording of DecisionCard on pending intention, no card on LOW auto-execute, Hero New Goal → `UI_COMMAND`. Without that, UI acceptance stays open.  
3. **Defects only** — if verification finds a contradiction (summary vs receipt, empty `{}` receipts, EA bypass), fix against the existing Gate 3 plans; do not invent architecture.

## Invalid Gate 5 claims

- Declaring Gate 5 or Wave 5 complete from Linux Cloud alone.  
- Using headless EventBus numbers as GUI budget close-out.  
- Shipping deployment automation because “Gate 5 sounds like release.”
