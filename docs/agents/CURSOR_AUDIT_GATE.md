# Cursor Audit Gate — Phase B UI Workflow

**Status:** ACTIVE  
**Audience:** Cursor / Tom (Repository Guardian) — sole coder + auditor as of 2026-07-22  
**Trigger:** Every Phase B UI PR (one evolution slice per PR)

---

## When to audit

- After a slice PR is opened (or landed on `main` pending formal write-up) → **audit before next slice starts**
- Do **not** stack the next evolution slice until Tom verdict is **PASS** (conditions fixed) and the audit report is on `main` when required by handover

---

## Audit inputs (required)

| Input | Source |
|-------|--------|
| PR diff | GitHub PR against `main` |
| PR body | Evidence template from `DEVIN_UI_HANDOVER.md` |
| Baseline | `origin/main` @ merge-base |
| Slice ID | PR-UI-E0x from evolution roadmap |

**Do not trust** PR claims without code/tests.

---

## Audit checklist

### 1. Scope & baseline

- [ ] Branch is from `origin/main`, not `phase-11a-command-center`
- [ ] One evolution slice only (no drive-by refactors)
- [ ] Matches `UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md` for that slice

### 2. Architecture (ADR-006 + UI Constitution)

- [ ] UI reads AppState / publishes EventBus only  
- [ ] No direct repository, SQLite, Ollama, or service calls from UI  
- [ ] No OperatorKernel / PlanningEngine / AgentCoordinator wired as authority  
- [ ] No second intake or execution path  

### 3. Primitive reuse

- [ ] Inspector: `InspectorHost` / `InspectorDock` extended, not replaced  
- [ ] World Model: `SelectionInspectorPanel` composed, not forked  
- [ ] Timeline: `TimelineRenderer` / `ExecutionTimelineDock` — no parallel `run_timeline` engine  
- [ ] Graph: `BaseGraphCanvas` — no `WorldGraphCanvas` engine  
- [ ] Phase 11 packages reused (`goal_dashboard/`, `agent_monitor/`, etc.)  

### 4. Evolution vs rewrite

- [ ] Existing views/panels extended, not greenfield duplicates  
- [ ] No regression of Phase 11 Mission Control surfaces  

### 5. AppState & state

- [ ] New AppState fields justified or composition-only  
- [ ] UI does not hold authoritative state  
- [ ] Context/global bar reads projections, not chat-local SoT  

### 6. Evidence

- [ ] Tests run (CI or stated local commands)  
- [ ] `verify_ui_constitution.py` if UI surfaces changed  
- [ ] Truth matrix updated if composition/wiring touched  

### 7. Regression

- [ ] Headless pytest path still valid  
- [ ] No removal of legacy paths without migration/redirect  

---

## Verdict rules

| Verdict | Meaning | Devin action |
|---------|---------|--------------|
| **PASS** | Slice meets scope + architecture + evidence | Merge allowed → next slice |
| **PASS WITH CONDITIONS** | Merge after listed fixes on same PR | Fix → re-audit → merge → next slice |
| **FAIL** | Architecture violation, wrong baseline, duplicate system, or missing evidence | Do not merge; fix or redesign slice |

### Automatic FAIL

- Branch from superseded `phase-11a-command-center` as SoT  
- OperatorKernel in `service_factory` without superseding ADR  
- New graph/timeline/inspector engine  
- Rewrite of Phase 11 workspace that duplicates `main` packages  
- Multiple evolution slices in one PR without approval  
- “Complete” claims without tests  

---

## Audit output format (Tom)

```markdown
## Tom Audit — PR-UI-E0x — <title>

**Verdict:** PASS | PASS WITH CONDITIONS | FAIL

### Executive summary
...

### Blockers (FAIL / CONDITIONS)
- file:line — issue

### Primitive reuse
PASS | FAIL — ...

### AppState
...

### Regression risks
...

### Next action for Devin
...
```

Post audit on PR or hand back to user. Devin waits.

---

## Program completion

Phase B UI program complete when:

1. PR-UI-E00 through E13 audited PASS (or accepted CONDITIONS) and on `main`  
2. Truth matrix + Canon still accurate  
3. Stray branches from hygiene table closed/deleted  
4. State Authority v1 tracked separately (not blocking UI merge if slices complied with rules)

---

## References

- `docs/agents/DEVIN_UI_HANDOVER.md`  
- `.agents/skills/tom-auditor/SKILL.md`  
- `docs/audits/REPOSITORY_TRUTH_CANON.md`  
- `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`
