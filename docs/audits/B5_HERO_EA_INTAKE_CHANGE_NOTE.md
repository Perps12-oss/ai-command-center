# Change Note — B5 Hero EA Intake (Fork 1)

**Branch:** `cursor/b5-hero-ea-intake-323d`  
**Baseline:** `origin/main` @ `2081127`  
**Pre-flight:** `docs/audits/CONSTITUTIONAL_PRE_FLIGHT_B5_HERO_EA_INTAKE.md`  
**Owner decision:** Fork 1 — `GOAL_SUBMIT_REQUEST` is internal post-authority.

---

## Publisher audit

| Production site | Finding |
|-----------------|---------|
| `ui/controller.py` | **Was** the only UI publisher (Hero via `view_manager._on_goal_new`) |
| `execution_authority_service._submit_plan` | Sole remaining production publisher |
| SA mutate (ADR-016) | Does not use this topic |

No other UI publishers found — Hero-only fix; no broad publisher refactor.

---

## Behaviour

1. `publish_goal_submit_request` publishes `UI_COMMAND` with `goal: <title>` (+ priority/description/workspace scope).
2. `classify_command` recognizes `goal:` → `INTENT_GOAL`.
3. EA `analyze` maps to capability `goal`; `_publish_decision` + `_admit` + state projection run.
4. EA `_submit_plan` emits stamped `GOAL_SUBMIT_REQUEST`.
5. `SingleGoalScheduler` **refuses** submits lacking `authority_decision`.

---

## Docs reconciled

- ADR-006 kept as authority rule.
- UI Constitution: Hero → EA intake, not scheduler topic.
- RUNTIME_AUTHORITY_MAP + GOALS_DUAL_PATH_INVENTORY updated.
- `scripts/verify_ui_constitution.py` forbids `GOAL_SUBMIT_REQUEST` in UIController.

---

## Tests

- `tests/test_b5_hero_ea_intake.py` — UI does not emit scheduler topic; EA order + stamp; fail-closed bypass.
- Goal dashboard UI tests updated to expect `UI_COMMAND`.
- Scheduler unit tests that published the topic without a stamp now include `authority_decision`.
