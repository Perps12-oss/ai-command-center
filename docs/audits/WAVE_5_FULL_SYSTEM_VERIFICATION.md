# Wave 5 — Full-system verification close-out

**Date:** 2026-08-17  
**Program wave:** Wave 5 — Intent → routing → authorization → execution → verification → receipt → state projection → timeline → explanation  
**Owner direction:** mark Wave 5 complete  
**Code baseline:** `origin/main` @ `f35cb98229df9f10b642347127541b38086f8c17`  
**Pre-flight:** `docs/audits/PREFLIGHT_WAVE5_CLOSEOUT.md`  
**Rule:** `docs/governance/PHASE_COMPLETION_RULE.md`

**Status on this branch tip:** close-out package ready.  
**Status on `origin/main`:** **not COMPLETE** until this file and the linked ledgers are merged. Until then maximum honest status is `PARTIALLY_IMPLEMENTED`.

This is the single place to check whether Wave 5 is done (same role as `WAVE_1_GATE_2_DECISIONS.md` for Wave 1).

---

## What Wave 5 is

Queue 1 Wave 5 is **verification of the live pipeline**, not a new feature wave and not Wave 5-as-release.

It verifies the Gate 4 runtime already on `main`:

| Stream | On `main` | Gate 4 merge |
|--------|-----------|----------------|
| A ADR-021 Decision Records | Yes | #190 |
| B ADR-022 autonomy bands | Yes | #192 |
| C ADR-023 M2–M4 | Yes | #193 |
| E ADR-024 M1 read-only federation | Yes | #188 |
| B5 ADR-006 hero `UI_COMMAND` | Yes | #168 / #189 |

Wave 5 is **not** Stream D isolation, Stream E vectors, Stream F Adapt, or Stream G Cross-OS.

---

## Pipeline evidence

| Step | Wired on `main` | Verification |
|------|-----------------|--------------|
| Intent | Hero New Goal → `UI_COMMAND` (`test_b5_hero_ea_intake.py`) | Keyword `goal_intake_hero` |
| Routing | Model router / local-only degrade (`test_model_strategy_gate4.py`) | `model_degradation`, `tier_pooling`, `orchestration` |
| Authorization | ExecutionAuthority admission; hero refuses submit without authority | `goal_intake_hero`; EA tests in orchestration suite |
| Execution | Orchestrator `tool.invoke` sole publisher (ADR-018); arch_lint R5 | `arch_lint.py --baseline`; orchestration tests |
| Verification | `TruthBoundary` on orchestration | `tests/orchestration/unit/test_truth_boundary.py` |
| Receipt | Orchestration receipt + Decision Record `receipt` (never empty `{}`) | `decision_record` tests |
| State projection | AppState `decision_record` / service snapshots | Headless `create_application()`; AppState tests in keyword set |
| Timeline | Execution-event history for Decision Records | `test_decision_record_history_via_execution_events` |
| Explanation | Decision Record evidence/policy/receipt/verification; DecisionCard only when pending | `decision_record` domain + orchestrator tests; Windows GUI operator attestation |

### Linux (Class A)

`docs/audits/GATE5_LINUX_VERIFICATION.md` on this branch:

- Keyword pytest: **175 passed**
- `arch_lint.py --baseline tests/arch_lint_baseline.json`: OK
- `verify_constitution.py`: PASS
- `ucgs_runner` + `ucgs_ci_gate`: PASS (S1)
- `create_application()` + startup/shutdown: OK

### Windows ARM64 GUI (Class B operator attestation)

`docs/audits/GATE5_WINDOWS_ARM64_GUI_VERIFICATION.md`: operator reported GUI working and verified on 2026-08-17. This Cloud host cannot launch `main.py`. No screenshots were attached.

---

## PHASE_COMPLETION_RULE inventory

| Condition | At `origin/main` `f35cb98` | After this PR merges |
|-----------|----------------------------|----------------------|
| 1. Phase features on `main` | Gate 4 stream **code** yes | Unchanged (no new code) |
| 2. Phase audits on `main` | Linux/Windows/Wave 5 ledgers **absent** | Present |
| 3. Constitution updates on `main` | No V4 amendment required | Queue/program docs updated |
| 4. No active branch holds Wave 5 **code** off `main` | True | True. Audits live on `docs/gate5-linux-verification` until merge. PR #194 holds EventBus Stage 1 docs (Wave 2 measurement), not Wave 5 pipeline code. |

**Wave 5 COMPLETE** is true only in the right-hand column.

---

## Explicitly still open (not Wave 5)

| Item | Status |
|------|--------|
| Wave 4 Goose Adapt (Stream F) | Not started; ADR-025 table accepted; Adapt rows still Wave 4 |
| Stream D isolation | Not unlocked; no ADR-026 |
| Stream E embeddings | UCGS `scope_embeddings` S5; ADR-024 condition |
| Wave 6 / Stream G Cross-OS | **Not opened** |
| Retired kernels (006/012/013/014) | Stay retired |

---

## Invalid claims

- Declaring Wave 5 complete from Linux Cloud alone (superseded by owner GUI attestation + this close-out, still requires `main`).
- Treating Wave 5 as app store / installer release.
- Opening Stream G because Wave 5 is marked (Wave 4 remains open).
- Equating operator GUI attestation with a Cloud-executed GUI session.
