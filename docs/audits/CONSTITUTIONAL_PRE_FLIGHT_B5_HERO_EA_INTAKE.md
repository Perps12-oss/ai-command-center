# Constitutional Pre-Flight — B5 Hero EA Intake (Fork 1)

**Status:** PRE-FLIGHT  
**Branch:** `cursor/b5-hero-ea-intake-323d`  
**Baseline tip:** `origin/main` @ `2081127`  
**Owner decision:** B5 fork 1 — `GOAL_SUBMIT_REQUEST` is internal post-authority; Hero routes through EA.

---

## 1. Authority read

| Level | Bearing |
|-------|---------|
| V4 Inv 1 | No shortcut — UI must not publish post-EA scheduler topics |
| ADR-006 | **Kept as authority rule.** EA sole user intake; `GOAL_SUBMIT_REQUEST` is downstream of EA |
| UI Constitution Art. 7 / Goal Dashboard | **Amend** — Hero publishes EA intake intent, not `GOAL_SUBMIT_REQUEST` |
| O-1 | No EventBus tier changes |
| Receipt boundary | Untouched — execution receipts remain on post-scheduler path |

---

## 2. Publisher audit (`GOAL_SUBMIT_REQUEST`)

| Site | Role | Action |
|------|------|--------|
| `ui/controller.py` `publish_goal_submit_request` | **Only current UI publisher** (Hero via `view_manager._on_goal_new`) | Remove direct publish; route via `UI_COMMAND` |
| `execution_authority_service.py` `_submit_plan` | Canonical post-decision emit | Keep |
| Tests / harness `bus.publish(...)` | Non-production | Update Hero-path tests; leave EA intake tests |

**Recorded fact:** Hero/Goal Dashboard is the only production UI publisher of `GOAL_SUBMIT_REQUEST` today. No other UI module publishes it. Broader publisher refactor deferred.

SA mutate (ADR-016) uses `submit_goal_for_state` → `submit_goal` and does **not** publish this topic.

---

## 3. Target path

```text
Hero New Goal
  → UIController.publish_goal_submit_request
  → UI_COMMAND (goal: <title>)     ← existing EA intake
  → EXECUTION_AUTHORITY_DECISION
  → workspace/state gate (_admit + StateAuthority.project)
  → GOAL_SUBMIT_REQUEST (authority_decision stamped, source=execution_authority)
  → SingleGoalScheduler
  → plan / EXECUTION_RUN_* / receipts
```

Forbidden:

```text
Hero → GOAL_SUBMIT_REQUEST → SingleGoalScheduler
```

---

## 4. Fail-closed

`SingleGoalScheduler._on_submit_request` refuses payloads lacking a non-empty
`authority_decision` dict. Direct UI (or any non-EA) publish cannot admit a goal.

---

## 5. Scope / non-goals

- Hero New Goal only (+ controller method used solely by Hero)
- `goal:` prefix classification (already advertised in command box / Mission chips)
- Docs: UI Constitution, RUNTIME_AUTHORITY_MAP, verify_ui_constitution gate
- Not: Phase C fossils, N-1 agent workspace, pause/resume topics, SA mutate rewrite
