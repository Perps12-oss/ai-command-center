# CLAUDE.md — Claude Code / non-Cursor implementation agent

**Status:** ACTIVE — subordinate operational guide  
**Authority:** Derives entirely from `PROJECT_CONSTITUTION_V4.md`, accepted ADRs, and `docs/governance/IMPLEMENTATION_GUIDE.md`. **Introduces no new governing rules.**  
**Audience:** Claude Code and any implementation agent that is not Cursor. Cursor agents still follow `AGENTS.md` + `.cursor/` rules.  
**Related audit:** `docs/audits/ACC_GOVERNANCE_AUDIT.md`

> Claude Code is an **implementation role**, never an authority. Switching tools must not require governance changes (`IMPLEMENTATION_GUIDE.md`).

---

## Authority

Read in this order before changing architecture-sensitive code (Article II + subordinate bindings):

1. `PROJECT_CONSTITUTION_V4.md` (supreme)
2. `AGENTS.md`, `docs/ARCHITECTURE_ENFORCEMENT.md` (Art II Level 2)
3. `docs/ARCHITECTURE.md`, contracts, topics (Art II Level 3)
4. **Accepted** ADRs under `docs/architecture/adr/` — binding under V4, **not** Art II Level 2; **Proposed ≠ binding**
5. Peer domain docs (`PERFORMANCE_CONSTITUTION.md`, `docs/UI_CONSTITUTION.md`) under V4 (V4 wins on conflict)
6. Repository truth on `origin/main` (code + audits)
7. Approved plans / roadmap (roadmap domain only)
8. Research (evidence only) / external repos (reference only)

Operational restatement: `docs/governance/IMPLEMENTATION_GUIDE.md`. If anything here conflicts with a higher authority, the higher authority wins and this file is corrected.

Do **not** treat this file, `.claude/`, Cursor, Devin, or any LLM as Level-1/2 authority.

---

## Before implementation

1. Read Constitution, Architecture, Contracts.  
2. Produce a **Constitutional Pre-Flight** under `docs/audits/` (or the path the task already uses).  
3. Implementation may not begin before pre-flight completion.

There is **no mechanical check** that Pre-Flight was written. Skipping it is a constitutional process failure even if CI is green.

---

## Architecture decisions

- Major changes use `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md` (multi-council), not informal ADR drafts alone.  
- Skill helpers such as `.agents/skills/` may assist review; they do not replace the framework.  
- Next free ADR number: **ADR-026** (024/025 assigned 2026-08-14 to Streams E/F at Wave 1 Gate 2 closure; ADR-007 was assigned twice historically — disclosed in `adr/README.md`). **This number will drift again** — `docs/architecture/adr/README.md` "Next free number" is the ultimate source; re-check it before trusting this line.  
- Roadmap text saying “ADR-001 Tool Invocation … ADR-006 Model Strategy” maps to **ADR-018–023**, not files 001–006.  
- Do not implement from **Proposed** ADRs as if Accepted.

---

## Verification order

Cheapest-first (same intent as `AGENTS.md` common commands):

```bash
python3 scripts/verify_constitution.py
python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json
python3 -m ruff check ai_command_center
python3 tools/ucgs_runner.py > .ucgs_last.yaml
python3 tools/ucgs_ci_gate.py .ucgs_last.yaml
APPDATA=/tmp/aicc_appdata python3 -m pytest -m "not slow"
```

**Green ≠ approved:**

- `.cursor` hooks and `tom-audit.yml` are **advisory** (do not fail closed).  
- `TOM_APPROVAL.lock` is optional, hand-maintained, **not CI-enforced**, and may be stale.  
- Tom the CI job ≠ Tom the LLM auditor.

When `ucgs_runner` is missing/`report_complete: false`, read `.cursor/rules/ucgs-v4-analysis.mdc` directly and apply its FAIL rules — do not ignore them because you are not in Cursor.

---

## Rules with no mechanical check

You are the enforcement for these (AST gates do **not** cover them). Treat violations as blockers:

| Rule | Source |
|------|--------|
| No global state (`GLOBAL_MODEL`, `CURRENT_VAULT`, …) | `AGENTS.md` / Inv |
| Host platform supremacy — external runtimes are capabilities only | Inv 13, ARI |
| All AI requests via ContextManager | Inv 6 |
| Telemetry firewall | Inv 9 |
| Single source of truth (no divergent authority copies) | Inv 11, Art. V |
| Non-circumvention (no wrappers/shims/migration paths that dodge gates) | Inv 12, Art. IX |
| Constitutional Pre-Flight before implementation | Art. X |
| Zero regression budget | Art. VII |
| UIQueue event-driven; no polling ≤100 ms | Art. XVII |
| No deprecated import shims | Art. XVII |
| `.result()` timeout on lifecycle shutdown | Art. XVII |
| Phase complete **only** on `main` | `PHASE_COMPLETION_RULE.md` |

Strongly gated already (do not weaken): UI isolation, no service→service calls, ADR-018 `tool.invoke` sole publisher.

---

## Tool parity (babysit-PR without Cursor)

`AGENTS.md` makes babysit-PR the default. The Cursor skill at `~/.cursor/skills-cursor/babysit/SKILL.md` may be absent. Satisfy the **intent**:

1. **Before commit** — if a PR exists: triage unresolved review comments and latest CI; fix in-scope issues.  
2. **After push / PR create** — until merge-ready: unresolved threads (incl. Bugbot), merge conflicts (merge latest base), in-scope CI failures.  
3. Use `gh pr view`, `gh pr checks`, `gh api` / review comments; never weaken CI to go green.  
4. Skip only if the user explicitly opts out or the task is unrelated to any PR.

Also:

- Phase-complete procedure: `docs/governance/PHASE_COMPLETION_RULE.md` (+ `.cursor/rules/phase-complete-on-main.mdc` as a readable copy of agent behavior).  
- Keep `.agents/skills/tom-auditor/SKILL.md` and `.cursor/skills/tom-auditor/SKILL.md` **byte-identical** when editing either.  
- Do not mirror `.devin/` empty stubs or `.windsurf/` constitution copies.

---

## Implementation auditing (Tom)

- Run Tom via `.agents/skills/tom-auditor/SKILL.md` + `docs/agents/tom-implementation-auditor.json`.  
- Independence: Tom cannot approve work Tom authored, fixed, or tested.  
- `TOM_APPROVAL.lock` / `.tom-audit/journal.jsonl` are optional ledgers — **not** proof of CI approval. Do not claim they gate merges.  
- `.tom-invocation-token` is retired; do not require it.

---

## Environment

| Fact | Action |
|------|--------|
| GUI is Windows-ARM64 only | Do not expect `main.py` to run on Linux x86_64 Cloud |
| Headless needs `APPDATA` | e.g. `APPDATA=/tmp/aicc_appdata` |
| Cloud Python | 3.12 documented; invoke tools as `python3 -m …` |
| `preflight_arm64.py` | Expects Ollama running for a full pass — env gate ≠ service availability |
| Product verification here | Prefer `create_application()` + pytest, not the desktop GUI |

---

## Current program

**Canonical planned-work queue:** [`docs/governance/IMPLEMENTATION_GUIDE.md`](docs/governance/IMPLEMENTATION_GUIDE.md) — **Queue 1: Strategic Runtime Program** ([`STRATEGIC_RUNTIME_PROGRAM.md`](docs/governance/STRATEGIC_RUNTIME_PROGRAM.md)).

**Active implementation work:** Waves 0–5 program milestones on `main` (see Queue 1). Wave 4 Goose Adapt close-out: [`docs/audits/WAVE_4_CLOSEOUT.md`](docs/audits/WAVE_4_CLOSEOUT.md) (**COMPLETE only on `main`**). Wave 6 / Stream G Gate 1 planning unblocked after that merge; Stream G code not started. Do not invent extra tickets from historical plans.

Section 9 of ADR-018–023 is **Accepted architecture already on `main`**. Remaining 021/022/023 envelopes are **Stream A–C** (checkpoints, not indefinite parking). EventBus isolation is **Stream D** (measure first; abandoned pool branch is not a merge candidate). Knowledge is **Stream E** (SoT ADR before any vector DB). Goose is **Stream F** (Adopt/Adapt/Reject). Cross-OS is the **only remaining strategic gate**. macOS Hotkey as a standalone strategic item is **dropped**.

**Still retired / not in the six streams** (`docs/audits/R1_UNGATED_STOP_LINE.md`):

- Live Predictive/Undo → ADR superseding 014 (**RETIRED** until then)
- Re-wire OperatorKernel / GoalEngine / PlanningEngine / AgentCoordinator → ADR superseding 006/012/013 (**RETIRED**; do not restore)

Fossil index: [`docs/governance/HISTORICAL_AND_RETIRED_WORK.md`](docs/governance/HISTORICAL_AND_RETIRED_WORK.md).

One implementation role consumes evidence from many sources; do not spawn overlapping implementation agents that rewrite the same surfaces.

---

## Evidence / efficiency / checkpoints

- Prefer repository truth on `origin/main` over branch tips and chat claims.  
- Class A = repo truth; Class B = research (reference); Class C = backlog — see IMPLEMENTATION_GUIDE.  
- Record Constitutional Pre-Flight and audits under `docs/audits/`; do not declare phases complete from feature branches.  
- Smallest sufficient change; no drive-by refactors; no new markdown except when the task is documentation.  
- After push: babysit until mergeable (section Tool parity).

---

## Excluded from this file

- Restatement of the full Constitution or full `AGENTS.md`  
- Cursor-only hook wiring as a dependency of correctness  
- Any rule that would need to change when the implementation tool changes
