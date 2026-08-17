# Gate 5 — Linux verification

**Date:** 2026-08-17  
**Host:** Linux x86_64 (Cursor Cloud)  
**Python:** 3.12.3  
**Tree under test:** `f35cb98229df9f10b642347127541b38086f8c17` (`origin/main` at verification time: merge of Gate 4 Stream C #193)  
**Pre-flight:** `docs/audits/PREFLIGHT_GATE5_LINUX_VERIFICATION.md`  
**Checklist file:** `GATE_5_VERIFICATION_CHECKLIST.md` is **not present** in this repository (search returned zero matches). The Linux command list from the operator request is the authority for this run.

**Verdict: PASS** — all Gate 4 keyword tests, canonical architecture/constitution/UCGS gates, and headless `create_application()` succeeded.

This ledger is **Linux verification** for Wave 5. Windows ARM64 GUI is operator-attested PASS in `docs/audits/GATE5_WINDOWS_ARM64_GUI_VERIFICATION.md`. Wave 5 close-out: `docs/audits/WAVE_5_FULL_SYSTEM_VERIFICATION.md` (**COMPLETE only on `main`**). EventBus isolation remains out of scope.

## Command results

| # | Requested command | Actual invocation | Exit | Result |
|---|-------------------|-------------------|------|--------|
| 1 | `pytest -k "decision_record or autonomy_escalation or model_degradation or tier_pooling or orchestration or federation_m1 or goal_intake_hero" -v` | `APPDATA=/tmp/aicc_appdata python3 -m pytest -k "…" -v --tb=short` | 0 | **PASS** — 175 passed, 1353 deselected, 22.03s |
| 2 | `python3 scripts/arch_lint.py --all` | Flag `--all` is **not a CLI option**. Canonical: `python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json` (default scan root is `ai_command_center/`) | `--all` → 2; baseline → 0 | **PASS** (canonical). Requested `--all` is a usage error, not a lint failure. |
| 3 | `python3 scripts/verify_constitution.py` | same | 0 | **PASS** — constitutional authority files present and governance checks clean |
| 4 | `python3 tools/ucgs_ci_gate.py` | Bare invocation prints usage and exits 2. Canonical: `python3 tools/ucgs_runner.py > .ucgs_last.yaml` then `python3 tools/ucgs_ci_gate.py .ucgs_last.yaml` | bare → 2; runner 0; gate 0 | **PASS** (canonical). UCGS summary: `verdict: PASS`, `risk_level: S1`, `report_complete: true` |
| 5 | `python3 -c "from ai_command_center.application import create_application; …"` | `APPDATA=/tmp/aicc_gate5_appdata python3 -c "…"` (`get_runtime_data_dir()` requires `APPDATA`) | 0 | **PASS** — printed `OK` then shutdown |

## Pytest keyword coverage

Expression:

```text
decision_record or autonomy_escalation or model_degradation or tier_pooling or orchestration or federation_m1 or goal_intake_hero
```

Outcome: **175 passed**, 1353 deselected. No failures, no skips in the selected set.

This expression covers Gate 4 streams on `main` (Decision Records, autonomy escalation, model degradation / tier pooling / orchestration, federation M1, goal-intake hero aliases). It is a verification filter, not a claim that every test in the repo ran.

## Architecture lint

`scripts/arch_lint.py` has no `--all` flag. Optional positional `root` defaults to the `ai_command_center` package (full-package scan). CI and `AGENTS.md` use the ratchet:

```bash
python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json
```

Stdout: `OK: no new architecture violations (4 baselined).`

## Constitution

```text
=== Constitution Governance Gate ===
PASS: constitutional authority files present and governance checks clean
```

## UCGS

`.ucgs_last.yaml` is gitignored. Gate output: `[UCGS PASS]`.

## Headless application

`create_application()` + `startup()` + `shutdown()` printed `OK`. GUI was not launched (Windows-ARM64 only).

## What this does not close

- EventBus isolation / ADR-026 (Stage 1 did not unlock isolation)
- Wave 4 Goose Adapt
- Wave 6 / Stream G Cross-OS
- Phase completion of Wave 5 until `WAVE_5_FULL_SYSTEM_VERIFICATION.md` is on `main`

Windows ARM64 GUI: see `docs/audits/GATE5_WINDOWS_ARM64_GUI_VERIFICATION.md` (operator-attested PASS, 2026-08-17).

## Reproduction

```bash
APPDATA=/tmp/aicc_appdata python3 -m pytest -k "decision_record or autonomy_escalation or model_degradation or tier_pooling or orchestration or federation_m1 or goal_intake_hero" -v
python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json
python3 scripts/verify_constitution.py
python3 tools/ucgs_runner.py > .ucgs_last.yaml
python3 tools/ucgs_ci_gate.py .ucgs_last.yaml
APPDATA=/tmp/aicc_gate5_appdata python3 -c "from ai_command_center.application import create_application; app = create_application(); app.startup(); print('OK'); app.shutdown()"
```
