# Constitutional Pre-Flight — ADR-006 §12 B5 Fork 1 record

**Date:** 2026-08-16  
**Task:** Document the already-merged B5 Fork 1 owner decision (`GOAL_SUBMIT_REQUEST` is internal post-authority; Hero New Goal intakes via `UI_COMMAND` → ExecutionAuthority) as ADR-006 §12 and align UI Constitution Articles 7–8 with Article 16. Docs only.  
**Status:** APPROVED

## Task Description

Code for B5 Fork 1 landed on `main` in #168 (`ec34287`). ADR-006 still ends at the 2026-07-21 revision history and does not record Fork 1. Article 16 already forbids UI publish of `GOAL_SUBMIT_REQUEST`; Articles 7–8 (Hero Immediate Action / Mission Hero) do not. This change adds the missing ADR addendum and the matching UI Constitution sentences. No product code.

## Authorities Reviewed

- `PROJECT_CONSTITUTION_V4.md` (Inv 1 ownership flow; Art. X; Inv 11)
- `AGENTS.md` / `docs/ARCHITECTURE_ENFORCEMENT.md`
- `docs/ARCHITECTURE.md`
- `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`
- `docs/UI_CONSTITUTION.md` Articles 7, 8, 16, 21
- `docs/audits/CONSTITUTIONAL_PRE_FLIGHT_B5_HERO_EA_INTAKE.md`
- `docs/audits/B5_HERO_EA_INTAKE_CHANGE_NOTE.md`
- `docs/audits/RUNTIME_AUTHORITY_MAP.md`

## Files Reviewed

- `ai_command_center/ui/controller.py` (`publish_goal_submit_request` → `UI_COMMAND`)
- `ai_command_center/services/execution_authority_service.py` (`_submit_plan`)
- `ai_command_center/services/goal_scheduler_service.py` (fail-closed without `authority_decision`)
- `scripts/verify_ui_constitution.py` (UIController must not reference `GOAL_SUBMIT_REQUEST`)
- `tests/test_b5_hero_ea_intake.py`

## Protected Assets Impacted

None in this PR (docs). ExecutionAuthority remains sole user intake (ADR-006).

## Sources of Truth Impacted

None. Scheduler topic remains post-authority; World Model / goals persistence unchanged.

## Architectural Invariants Impacted

- **Inv 1:** UI must not shortcut EA by publishing scheduler topics.
- **Inv 2:** UI publishes events only.
- **Inv 11:** No second intake SoT.

## Contracts Impacted

Event topics: `UI_COMMAND` (intake), `GOAL_SUBMIT_REQUEST` (EA-only). No new topics.

## Gate Impact Assessment

Not a Strategic Runtime stream Gate 4. Records a closed Phase B item already on `main`. Does not authorize OperatorKernel or dual intake.

## Historical Gate Impact

B5 Fork 1 implementation already merged (#168). This is the missing ADR/UI-constitution close-out.

## Regression Risk

Docs only. `verify_ui_constitution.py` still reports 9 pre-existing Command Center label/hero failures unrelated to this amendment.

## Constitutional Status

APPROVED
