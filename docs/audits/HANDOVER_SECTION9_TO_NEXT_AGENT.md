# Handover — Section 9 polish complete; next ungated work

**Date:** 2026-08-07  
**Author context:** Cloud agent run that shipped ADR-018 M3 + 019 harden + CI unblock  
**Tip of `main`:** `16f549e` (Merge #161)  
**Authority:** `PROJECT_CONSTITUTION_V4.md` → `AGENTS.md` → ADRs 018–023

---

## 1. One-line status

**Section 9 follow-ons + 018 M3 / 019 harden are on `main` via [#161](https://github.com/Perps12-oss/ai-command-center/pull/161).** Phase 5 Async EventBus remains **approval-gated** — do not start without Performance Investigation Report + human approval.

---

## 2. What landed (trust `main`, not branches)

| PR | Squash / tip | Content |
|----|--------------|---------|
| [#157](https://github.com/Perps12-oss/ai-command-center/pull/157) | `cd35f01` | First Section 9 slice: 018 M1/M2/M4, 019 M1–M4, 020 M1–M2, 021/022 M1 (+ TruthBoundary wire), 023 M1–M2 |
| [#161](https://github.com/Perps12-oss/ai-command-center/pull/161) | `16f549e` | **018 M3** arch lint R5; **019** richer `wm_snapshot`; multi-step fail→replan test; CI unblock for TruthBoundary facts + replan/goal lifecycle |

Pre-flights (historical):

- `docs/audits/CONSTITUTIONAL_PRE_FLIGHT_SECTION9_FOLLOWONS.md`
- `docs/audits/CONSTITUTIONAL_PRE_FLIGHT_SECTION9_018M3_019.md`

---

## 3. ADR 018–023 milestone board (repo truth)

| ADR | Done on `main` | Remaining (highest leverage next) |
|-----|----------------|-----------------------------------|
| **018** Tool invocation | M1–M4 | Optional: live LLM planner assist *only* via `PLAN_REQUEST` / PlannerService (contract exists; no XGrammar) |
| **019** Planning | M1–M4 | Optional: richer stuck UX / Decision Record escalate polish |
| **020** Memory | M1–M2 | M3 only if ADR-008 proceeds; M4 doc honesty |
| **021** Explainability | M1 + TruthBoundary live wire + DecisionCard slice | **M3** Evidence/Approvals/Mission Control surfaces; **M5** DecisionCard↔pending approvals |
| **022** Confidence | M1 (+ emit on escalate paths) | **M2–M4** compute at more gates; threshold escalation; UI projection |
| **023** Model strategy | M1–M2 | **M3** local-only replan/destroy + HITL; **M4** telemetry model/provider/reason |

Council ADRs: `docs/architecture/adr/ADR-018_*.md` … `ADR-023_*.md`  
Index: `docs/architecture/adr/README.md`  
Framework: `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md`

---

## 4. Critical fixes in #161 (do not regress)

These were **broken on `main` after #157** and fixed in #161:

1. **TruthBoundary facts** — Provider facts (`time`, `launched`, calendar keys, …) must travel `ToolResult.facts` → `TOOL_RESULT` → orchestrator `step_outputs[].facts` → `enrich_execution_facts` → TruthBoundary. Dropping facts re-breaks time/calendar/launch golden tests.
2. **Replan without planner** — If `PLAN_REPLAN_REQUEST` gets no sync handler, orchestrator must `_fail_run` (do not leave `replanning=True` forever).
3. **GoalScheduler vs replan** — Ignore `PLAN_GENERATED` when `replan: True`. Otherwise a second `EXECUTION_RUN_REQUEST` starts and the active goal never clears (Program 3 `remember:` stalls).
4. **Arch lint R5** — Only `services/execution_orchestrator_service.py` may `publish(TOOL_INVOKE|\"tool.invoke\")`.

Key files:

```
scripts/arch_lint.py                          # R5
ai_command_center/core/tools.py               # ToolResult.facts
ai_command_center/orchestration/capability_tools.py
ai_command_center/orchestration/verification/execution_truth.py
ai_command_center/services/execution_orchestrator_service.py
ai_command_center/services/goal_scheduler_service.py
ai_command_center/services/tool_executor_service.py
docs/architecture/INTENTION_CONTRACT.md
docs/architecture/MEMORY_BOUNDARY.md
```

---

## 5. Recommended next work (ungated)

**Do not start Phase 5** (`docs/plans/PHASE_5_ASYNC_EVENTBUS_PLAN.md`) without Performance Investigation Report + human approval (`R1_UNGATED_STOP_LINE.md`, IMPLEMENTATION_GUIDE Queue 1 #4).

Highest-leverage ungated continuations (pick one track):

1. **021 M3 / M5** — Surface Decision Records in Evidence / Approvals / Mission Control; wire DecisionCard to pending approvals (UI projection only; no business logic in UI).
2. **022 M2–M3** — Compute AutonomyScore at more gate points; escalate below threshold without bypassing WRITE_DESTROY.
3. **023 M3** — Prove replan/destroy paths on local-only config with HITL (no cloud required).
4. **020 M3** — Only if ADR-008 compaction is in scope; keep summaries derived, never SoT.

Before architecture-sensitive commits:

```bash
python3 tools/ucgs_runner.py > .ucgs_last.yaml
python3 tools/ucgs_ci_gate.py .ucgs_last.yaml
python3 scripts/verify_constitution.py
```

Produce Constitutional Pre-Flight (Art. X) before implementing.

---

## 6. Phase 5 (gated) — point summary for later

- **Status:** PARTIAL; **approval-gated**
- **Missing:** `tiered_dispatch_policy.py`, `async_dispatch_queue.py`, ucgs profile pools, async tests, exit 5.4
- **Partial on main:** `dispatch_policy.py` classification; optional `EVENTBUS_DISPATCH_QUEUE` / R4b–R4c hooks in `event_bus.py` (default **off**)
- **Docs:** `docs/architecture/ASYNC_EVENTBUS_POLICY.md`, `docs/plans/PHASE_5_ASYNC_EVENTBUS_PLAN.md`

---

## 7. Environment / verification (Cloud)

- GUI `main.py` is Windows-ARM64 only — use headless: `APPDATA=/tmp/aicc_appdata`
- Tests: `python3 -m pytest` (~2 min); fast: `-m "not slow"`
- Lint: `python3 -m ruff check ai_command_center`
- Arch: `python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json`
- Branch naming: `cursor/<descriptive-name>-621d` (or current run’s suffix policy)
- PRs: ManagePullRequest tool; babysit until merge-ready (default)

---

## 8. Open PRs (context only — may change)

At handover time: [#162](https://github.com/Perps12-oss/ai-command-center/pull/162) exec scrubber (unrelated UI). Re-check `gh pr list` before starting.

---

## 9. Non-negotiables for the next agent

- Ownership: `UI → AppState → EventBus → Services → Repositories → Storage`
- No LLM → `TOOL_INVOKE` bypass (R5)
- No ReAct loop inside orchestrator; replan is bus-visible via `plan.replan.*`
- No Phase 5 / Goose / Predictive-Undo live-wire without gates
- Babysit PRs; do not weaken CI
- Main is the only truth for “phase/feature complete”

---

## 10. Suggested first prompt for the new agent

> Continue ungated Section 9: implement ADR-021 M3 (Decision Record surfaces in Evidence/Approvals/Mission Control) + M5 DecisionCard wiring. Read Constitution, Architecture, ADR-021, produce Constitutional Pre-Flight, then implement. Do not start Phase 5. Babysit PR to merge-ready.
