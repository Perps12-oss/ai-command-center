# Devin UI Implementation Handover

**Status:** ACTIVE  
**Date:** 2026-07-21  
**Audience:** Devin (builder — UI / frontend)  
**Auditor:** Cursor + Tom (Repository Guardian)  
**Baseline:** `origin/main` only — never `phase-11a-command-center`  
**Governance on main:** PR #83–#84 merged (Canon, DOC_HYGIENE, ADR-006, R1, State Authority contract)

---

## Roles

| Role | Owner | Must |
|------|-------|------|
| **Builder** | Devin | Implements one scoped PR at a time from the evolution roadmap |
| **Auditor** | Cursor (Tom) | Evidence audit before next PR starts |
| **Merge authority** | You | Merge only after Tom **PASS** or **PASS WITH CONDITIONS** (conditions fixed) |

**Cursor does not implement UI.** Devin does not self-certify architecture compliance.

---

## Mandatory workflow (stop gate)

```text
1. git fetch origin main && git checkout -b devin/<slice>-2c79 origin/main
2. Implement ONE evolution slice (PR-UI-E0x)
3. Run verification (below)
4. Open PR → STOP
5. Wait for Cursor/Tom audit on that PR
6. If FAIL → fix same PR, re-audit
7. If PASS / PASS WITH CONDITIONS (fixed) → merge → then only then start next slice
```

**Never stack multiple evolution PRs without audit between them.**  
**Never branch from `phase-11a-command-center`.**

### PR description must include (audit evidence)

```markdown
## Slice
PR-UI-E0x — <title>

## Baseline
origin/main @ <sha>

## Files changed
- ...

## Primitives reused (mandatory)
- [ ] InspectorHost / InspectorDock
- [ ] TimelineRenderer / ExecutionTimelineDock
- [ ] BaseGraphCanvas (no new graph engine)
- [ ] Existing Phase 11 workspace shells (evolve, not rewrite)

## AppState
- Fields added: none | list with justification
- Composition-only: yes/no

## Tests
- [ ] python3 -m pytest -m "not slow" (or subset with path)
- [ ] python3 scripts/verify_ui_constitution.py (if UI)

## Known risks / deferrals
- ...
```

---

## Implementation sequence (Phase B UI)

**Roadmap:** [`docs/architecture/UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md`](../architecture/UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md)

Land in order — dependencies are explicit in that doc.

| Order | Slice | Focus | Audit focus |
|------:|-------|-------|-------------|
| 1 | PR-UI-E00 | Consolidation & relocation (home→command_center, inspector tabs) | No regressions; evolve not delete |
| 2 | PR-UI-E01 | Universal inspector extension | Single inspector rail; compose `SelectionInspectorPanel` |
| 3 | PR-UI-E02 | Global context bar | Extend TopBar (Art. 17); state from AppState |
| 4 | PR-UI-E03 | OS palette | Provider registry; no shadow command path |
| 5 | PR-UI-E04 | Navigation shell | Sidebar groups; `command_center` default |
| 6 | PR-UI-E05–E09 | Memory, Brain, Goal, World, Agents workspaces | **Evolve** existing views + packages on `main` |
| 7 | PR-UI-E10–E12 | Evidence, Operations, Graph workspace | Reuse timeline + graph primitives |
| 8 | PR-UI-E13 | Insights placeholder | Informative empty state (Art. 18) |

### Parallel track (not Devin UI — do not start in UI PRs)

| Track | Owner | Gate |
|-------|-------|------|
| State Authority v1 | Backend / separate PRs | [`STATE_AUTHORITY_CONTRACT.md`](../architecture/STATE_AUTHORITY_CONTRACT.md) |
| OperatorKernel | **Forbidden** as authority (ADR-006) | Research/tests only |

UI slices must not mask missing state consumption (no chat-only context for workspace decisions).

---

## Architecture rules (non-negotiable)

From ADR-006, UI Constitution, Canon:

1. **UI → AppState → EventBus → Services** — no repo/SQLite/Ollama from UI  
2. **Evolve** Phase 11 on `main`: `goal_dashboard/`, `agent_monitor/`, `execution_center/`, `world_model/*`  
3. **Reuse primitives** — no `WorldGraphCanvas` engine, no `run_timeline` engine, no third inspector OS  
4. **OperatorKernel** — do not wire into `service_factory`  
5. **AppState** — prefer composition; new fields need justification vs Phase 11 “no new fields” covenant  
6. **CustomTkinter** — no web/Electron parallel UI  

Inventory SoT: [`REPOSITORY_TRUTH_CANON.md`](../audits/REPOSITORY_TRUTH_CANON.md)

---

## Known deficiencies (do not repeat)

| Deficiency | Correct behavior |
|------------|------------------|
| Audited `phase-11a` instead of `main` | Always `origin/main` |
| Treating packages as “concept only” | `goal_dashboard/`, `BaseGraphCanvas`, etc. exist on `main` |
| Rewrite language for Phase 11 workspaces | Evolve `GoalView`, `AgentsView`, `WorldExplorerView`, … |
| Duplicate graph engine | `BaseGraphCanvas` + adapters only |
| Duplicate timeline | `TimelineRenderer` + `ExecutionTimelineDock` |
| Fork inspector | Extend `InspectorHost`; compose `SelectionInspectorPanel` |
| OperatorKernel as live path | ADR-006: ExecutionAuthority canonical |
| False COMPLETE in plans | Code verification + Tom audit |
| Stacking PRs without audit | One slice → audit → merge → next |

---

## Branch & PR hygiene (tidy before / during Phase B)

Execute as governance PRs or with merge authority — Devin should not branch from these.

| Item | Status | Action |
|------|--------|--------|
| PR #75 `phase-11a-command-center` | OPEN, superseded | **Close** — content on `main` via #76–#79 |
| Branch `origin/phase-11a-command-center` | 13 ahead / 8 behind `main` | **Delete** after PR #75 closed |
| PR #66 `cursor/timeline-undo-p1-6c6b` | OPEN | Triage — undo landed #74; likely **close** |
| PR #81 `cursor/phase-12-state-intelligence-0fbc` | OPEN | **Separate program** — not Phase B UI; audit on its own |
| `origin/cursor/state-authority-migration-6a56` | Merged via #80 | **Delete** remote branch |
| `origin/cursor/runtime-first-execution-authority-6a56` | Stale | Review → **delete** if empty vs `main` |
| `origin/feature/planner-evolution-phase-c0-constitution` | 56 behind | **Stale** — confirm with owner or delete |

After each merge: `git fetch origin main` before new work.

---

## Verification before every PR (Devin)

```bash
export APPDATA=/tmp/aicc_appdata
python3 -m pytest -m "not slow"
python3 -m ruff check ai_command_center
python3 scripts/verify_ui_constitution.py
python3 scripts/verify_constitution.py
```

For inspector/palette/shell PRs also:

```bash
python3 -m pytest tests/ui/
```

---

## Cursor audit gate (what Tom checks)

See [`CURSOR_AUDIT_GATE.md`](CURSOR_AUDIT_GATE.md).

Verdicts: **PASS** | **PASS WITH CONDITIONS** | **FAIL**

Devin **must not** open the next slice until verdict is PASS (conditions merged).

---

## References

| Doc | Role |
|-----|------|
| `UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md` | Slice scope & deps |
| `PHASE_R1_RUNTIME_RECONCILIATION.md` | Program priority order |
| `ADR-006_EXECUTION_AUTHORITY_CANONICAL.md` | No OperatorKernel authority |
| `STATE_AUTHORITY_CONTRACT.md` | State layer (parallel) |
| `IMPLEMENTATION_TRUTH_MATRIX.md` | Exists / Wired / Tested |
| `DOC_HYGIENE.md` | Doc archive rules |

---

## Start command (Devin)

```bash
git fetch origin main
git checkout -b devin/pr-ui-e00-consolidation-2c79 origin/main
# implement PR-UI-E00 only
# open PR → STOP → wait for Cursor audit
```
