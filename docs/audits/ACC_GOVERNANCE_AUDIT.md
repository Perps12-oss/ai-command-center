# ACC Governance Audit

**Status:** ACTIVE — historical findings inventory (A–F); **living-document alignment executed** per owner decision register on `cursor/governance-alignment-323d` (Guide/adr README hierarchy wording, UI windsurf SUPERSEDED, research ID/provenance labels, tool-neutral adapters). This file’s narrative may still describe pre-alignment wording for evidence; prefer current living docs for operative rules.  
**Audit date:** 2026-08-11  
**Audit baseline:** `origin/main` @ `16f549e` (2026-08-07) — canon read via `git show origin/main:<path>`; no checkout of foreign branches, no fetch required for the audit pass  
**Documentation tip:** landed on `origin/main` lineage at/after `417b8e9` (see Related)  
**Authority:** Derives from `PROJECT_CONSTITUTION_V4.md` and restates findings only. **Introduces no new governing rules.**  
**Related:** `docs/governance/IMPLEMENTATION_GUIDE.md`, `docs/architecture/adr/README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/audits/R1_UNGATED_STOP_LINE.md`

> **Why that baseline:** `AGENTS.md` (“main is the only truth”) and `docs/governance/IMPLEMENTATION_GUIDE.md` — item 3 of the operational precedence list — exist on `origin/main`. Feature-branch checkouts that predate the governance layer are not authoritative for this audit.

> **Caveat (structural):** Any working tree that is hundreds of commits behind `origin/main` may be missing IMPLEMENTATION_GUIDE, the ADR framework, ADR-012–023, newer verifiers, and Tom v2. Work done in such a tree is governed by rules it does not contain. Prefer `origin/main` tip.

---

## A. Canonical authority model

`PROJECT_CONSTITUTION_V4.md` Article II states six levels:

```text
Constitution → AGENTS.md / ARCHITECTURE_ENFORCEMENT.md
  → ARCHITECTURE.md + contracts.py + topics.py
  → phase docs → verification → implementation
```

Article 0 adds the rule that matters for section B: **“Verification shall never redefine requirements.”**

`docs/governance/IMPLEMENTATION_GUIDE.md` restates a seven-level **operational** order that inserts ADRs at level 2 and peer constitutions beside the Constitution:

| # | Source |
|---|--------|
| 1 | Constitution (+ peers `PERFORMANCE_CONSTITUTION.md`, `docs/UI_CONSTITUTION.md`) |
| 2 | ADRs |
| 3 | Architecture contracts |
| 4 | Repository truth on `origin/main` |
| 5 | Roadmap / approved plans |
| 6 | Research |
| 7 | External repos |

The guide is explicit that it “derives its authority entirely from” the Constitution and ADRs and “introduces no new governing rules.”

### Gaps in the restatement vs Article II

1. Peer constitutions and the ADR level appear nowhere in Article II.  
2. `docs/architecture/adr/README.md` places ADRs at “Level 2” — the slot Article II gives `AGENTS.md`.  
3. The Constitution has **not** been amended to record either.

### Tool-neutrality — stated deliberately, then contradicted

The guide is unambiguous: the identity of the implementation agent is not architecturally significant; switching tools must not require governance changes. History of the guide (tool-agnostic refactor 2026-07-27; multi-council ADR framework 2026-08-05) is consistent with a living operational guide.

But tool-specific privilege survives above and beside it:

| Surface | Problem |
|---------|---------|
| `AGENTS.md` babysit-PR block | Level-2 authority makes babysit default; procedure delegates to `~/.cursor/skills-cursor/babysit/SKILL.md` (outside the repo) |
| `AGENTS.md` Cursor Cloud block | Entire Cloud-specific instructions live in the same Level-2 document |
| `docs/agents/CURSOR_AUDIT_GATE.md` | Audience “Cursor / Tom”; verdict table headed “Devin action”; dated before the tool-agnostic refactor; still ACTIVE |

Nothing in the repository privileges Claude Code. The **declared** model is tool-neutral; the **residual** model assumes Cursor.

### ADR inventory

Under `docs/architecture/adr/` (25 files at audit time):

**Accepted (14):** 006 Execution Authority Canonical · 007a AppState Notification Storms · 012 Goals Phase 9 · 013 Planning/AgentCoordinator (research-only) · 014 Predictive Undo (research-only) · 015 SA Mutate Memory · 016 SA Mutate Goals · 017 SA Mutate WEA (remain outside) · 018 Tool Invocation (Hybrid B-primary) · 019 Planning · 020 Memory · 021 Explainability · 022 Confidence & Autonomy · 023 Model Strategy  

**Proposed (9+):** 001 Persistence · 002 Scheduler · 003 Observer Flow · 004 Runtime Approval · 005 World Model Authority · 007b Provider Registry · 008 Conversation Compaction (narrowed by 020) · 009 Tool Confirmation Router (narrowed by 018) · 010 Modular Tool Inspection · 011 Telemetry Backends  

**Flags:**

- **ADR-007 collision** — assigned twice (`APPSTATE_NOTIFICATION_STORMS`, `PROVIDER_REGISTRY`). Disclosed in `adr/README.md` (“Number collision”) and `ARCHITECTURE_DECISION_FRAMEWORK.md`. Next free number: **ADR-024**.  
- **Proposed at Level 2** — ~⅓ of the ADR corpus is “binding intent undecided”; precedence tables alone do not say which ADRs bind.  
- **Roadmap label shadow** — informal “ADR-001 Tool Invocation … ADR-006 Model Strategy” maps to **018–023**, not files 001–006. Live misreading hazard; `adr/README.md` warns.

---

## B. Verification chain

Cheapest-first order (from `AGENTS.md` Cloud / common commands, reordered):

1. `scripts/verify_constitution.py` — authority file existence + AST  
2. `scripts/arch_lint.py --baseline` — AST boundary rules (one package)  
3. `ruff`  
4. `tools/ucgs_runner.py` / `tools/ucgs_ci_gate.py` (staged diff)  
5. `pytest` (~2 min)

| Script | Checks |
|--------|--------|
| `verify_constitution.py` | Authority files exist; duplicate authority docs (**regex `architecture.md` only**); UI AST imports of repositories/db/services; `shell=True` allowlist; services importing named legacy `db.*` modules |
| `arch_lint.py` | R1 UI→services; R2 `*Service` instantiation outside composition roots; R3 AppState attribute assignment; R4 service→peer imports; R5 ADR-018 M3: only `ExecutionOrchestratorService` may publish `tool.invoke`. Ratchet: `tests/arch_lint_baseline.json` |
| `ucgs_runner.py` | layer_imports, forbidden_patterns, large_commit, contract_drift |
| `ucgs_ci_gate.py` | Blocks on FAIL or risk S4/S5 per `enforcement_mode` |
| `preflight_arm64.py` | Python ≥3.11, ARM64, RAM, baseline.json, Ollama HTTP + PE arch, deps, wheel audit |

**Blocking in CI:** `.github/workflows/ucgs.yml` (`UCGS_ENFORCEMENT: block`) and `tests.yml` (matrix + arch_lint, ruff, bandit, pytest).

**Local gap:** `.pre-commit-config.yaml` configures constitution, arm64-binary-scan, arch-lint, bandit — but clones that install the UCGS-generated `.git/hooks/pre-commit` run UCGS/arch_lint only. Constitution / ARM64 scan / bandit may not run on local commits despite being configured.

**Advisory only:** `.cursor` hooks (`failClosed: false`); `tom-audit.yml` / `tom-deep-audit.yml` (comment / print; never fail the job).

**Exists but unwired / dispatch-only:** `arm64-gate.yml` (workflow_dispatch); `preflight_arm64.py`; `verify_ui_constitution.py`; `verify_runtime_identity.py`; phase verify scripts; several specialized verifiers.

**Stale enforcement docs:** `README.md` still says UCGS “warn mode by default” while `ucgs.config.yaml` has `enforcement_mode: block`. `.cursor/rules/ucgs-v5-project.mdc` says “Pre-commit warns only” while an installed UCGS hook may block.

---

## C. Non-negotiable rules — mechanical backing

Of 17 stated non-negotiables: **4 strong**, **2 partial**, **11 markdown-only**.

| Rule | Backing |
|------|---------|
| UI isolation | Strong — arch_lint R1 + verify_constitution AST + UCGS layer_imports |
| No direct service-to-service calls | Strong — arch_lint R4 (+ R2) |
| `tool.invoke` sole publisher (ADR-018 M3) | Strong — arch_lint R5 |
| Service wiring only in `service_factory.py` | Partial — R2 covers services; `_register_views()` unchecked |
| Repository ownership of persistence | Partial — blocks named legacy modules only |
| No global state | Markdown only (R3 is AppState mutation, different rule) |
| Host platform supremacy (Inv 13 / ARI) | Markdown only — ARI file existence checked |
| All AI requests via ContextManager | Markdown only in enforced path |
| Telemetry firewall | Markdown only |
| Single source of truth | Nearly none — duplicate check is `architecture.md` regex only |
| Non-circumvention | Markdown only |
| Constitutional Pre-Flight | Markdown only |
| Zero regression budget | Markdown only; partly proxied by ratchets |
| UIQueue event-driven (no ≤100 ms polling) | Markdown only |
| No deprecated import shims | Markdown only |
| `.result()` timeout on lifecycle shutdown | Markdown only |
| Phase complete only on main | Markdown only — no script diffs deliverables vs `origin/main` |

**Pattern:** what an AST can see is enforced. Ownership, process, and source-of-truth substance rest on reviewer / agent discipline.

---

## D. Tool-specific inventory

### `.cursor/`

Largest surface: `hooks.json` + advisory hook scripts; alwaysApply rules. `rules/ucgs-v4-analysis.mdc` is real governance content that exists only inside Cursor (immutable FAIL rules, locked pipeline, 8-section output).

Babysit-PR is **both** a repo-level rule (`AGENTS.md`) and a Cursor-only mechanism (`.mdc` + hooks + home-directory skill).

### `.devin/`

`enhance.md` / `tom.md` are empty blobs on canon — dead scaffolding.

### `.windsurf/`

Plan docs none of which are authorities. **`.windsurf/plans/UI_CONSTITUTION-ff006d.md`** is a divergent copy of `docs/UI_CONSTITUTION.md` — peer-constitution duplication under Invariant 11 that `verify_constitution` cannot see (pattern is `architecture.md` only). Prefer **delete**, not mirror.

### Two things named Tom

1. **Tom the LLM auditor** — `.agents/skills/tom-auditor/SKILL.md` + `docs/agents/tom-implementation-auditor.json`. Hierarchy: runtime > source > tests > docs > claims. Independence Rule (cannot approve own work). Process ≠ outcome.  
2. **Tom the CI job** — `tom-audit.yml` counts files / greps title / checks tests touched; always reports success. Config thresholds (`max_violations`, `arch_drift_tolerance`) are never evaluated.

`TOM_APPROVAL.lock` is a hand-serialized verdict (`ci_enforced: false` / not CI-enforced). Skill-copy parity (`.agents` ↔ `.cursor`) is required; on clean `origin/main` both match.

### Claude Code parity gaps (consequence)

1. Babysit-PR — mandatory; Cursor skill may be absent → satisfy **intent** via `gh` (comments, conflicts, CI) without the skill file.  
2. `ucgs-v4-analysis.mdc` — read directly when UCGS report incomplete.  
3. Commit-time UCGS — run `tools/ucgs_runner.py` + gate explicitly.  
4. Phase-complete — follow `docs/governance/PHASE_COMPLETION_RULE.md` (not only the `.mdc`).  
5. Tom — use `.agents/skills/tom-auditor/`; keep skill copies identical.  
6. Do not replicate `.devin/` or `.windsurf/` constitution copies.

---

## E. Environment

| Item | Notes |
|------|--------|
| GUI | Windows-ARM64 only (`main.py` / `is_arm64()`); Cloud x86_64 cannot launch desktop UI |
| Headless | Requires `APPDATA` (e.g. `/tmp/aicc_appdata`) |
| Cloud Python | Documented 3.12; floor ≥3.11; local ARM hosts may run 3.14 (clears floor; not in CI matrix) |
| `preflight_arm64.py` | Hard-fails if Ollama not running — conflates env gate with service availability |
| ARM64 hard gate | `arm64-gate.yml` dispatch-only; binary scan in `tests.yml` is `continue-on-error` |

---

## F. Program boundary

**Closed:** Phase B UI remediation (#105); R1 P1–P4; P5 via ADR-014; Stage 2 soft-shadow; SA.mutate track CLOSED (live = WM nodes/edges + `store_memory` + `submit_goal`; WEA outside per ADR-017); ADR-018–023 accepted.

**Active:** Section 9 implementation of ADR-018–023; performance track (PERF-002/003/004) under `PERFORMANCE_CONSTITUTION.md`.

**Hard stops** (from `R1_UNGATED_STOP_LINE.md`):

| Blocked | Gate |
|---------|------|
| Phase 5 Async EventBus | Performance Investigation Report + human approval |
| Goose / external patterns | Stage 3 + Integration Proposal + ADR |
| Live-wire Predictive/Undo | ADR superseding ADR-014 |
| Re-wire OperatorKernel / GoalEngine / PlanningEngine / AgentCoordinator | ADR superseding 006/012/013 |
| Platform hotkey/tray live wire | Phase 11 backlog |

Feature branches that add Goose research ADRs while predating the governance layer are Class B / Queue 2 / Stage 3 — gated; do not treat as canon.

---

## Conflicts / clarifications (meta)

1. No prior report in this shape existed under `docs/audits/` before this document.  
2. `IMPLEMENTATION_GUIDE.md` path must be read from `origin/main` if a checkout predates it.  
3. `AGENTS.md` references ARI directly; both ARI and `docs/ARCHITECTURE.md` are required by `verify_constitution.py`.  
4. `.tom-invocation-token` is retired by Tom v2 (gitignore); local residue is not a live mechanism.  
5. Babysit-PR is genuinely both: repo-level rule + Cursor-only mechanism.  
6. Multi-LLM is accurate for **evidence gathering**; IMPLEMENTATION_GUIDE requires **one implementation role** for code changes.

---

## Recommended follow-ons (not done by this audit)

| Priority | Action | Owner surface |
|----------|--------|----------------|
| P1 | Fix stale “warn mode” wording in `README.md` / ucgs-v5 rule | Docs |
| P1 | Align local hooks with `.pre-commit-config.yaml` or document UCGS-only install | Tools / docs |
| P2 | Amend Article II (or explicitly demote IMPLEMENTATION_GUIDE ADR slot) | Constitution / ADR |
| P2 | Delete `.windsurf` UI constitution duplicate | Hygiene |
| P2 | Narrow `CURSOR_AUDIT_GATE.md` audience / retract Devin-only language | Agents docs |
| P3 | Mechanical checks for high-value markdown-only rules (globals, ContextManager, phase-vs-main) | Verifiers |
| P3 | Refresh or mark stale `TOM_APPROVAL.lock` | Operator |

---

## Verdict

**COMPLETE with caveats.** Sections A–F answer against canon at `16f549e`. Structural caveat: do not implement from trees that lack the modern governance layer — use `origin/main`.
