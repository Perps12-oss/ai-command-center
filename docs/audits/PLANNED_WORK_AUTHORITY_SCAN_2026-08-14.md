# Planned-Work Authority Chain Scan — 2026-08-14

**STATUS:** AUDIT RECORD — **NOT AN IMPLEMENTATION QUEUE**

**HISTORICAL / NON-AUTHORITATIVE as an implementation plan**

This document is a point-in-time read-only scan of the planned-work authority chain.
It is **evidence**, not authority, and it creates no work. Do **not** implement from it.

Canonical planned-work queue: [`docs/governance/IMPLEMENTATION_GUIDE.md`](../governance/IMPLEMENTATION_GUIDE.md) — **Queue 1 is EMPTY**.
Fossil index: [`docs/governance/HISTORICAL_AND_RETIRED_WORK.md`](../governance/HISTORICAL_AND_RETIRED_WORK.md)
Hygiene: [`docs/governance/DOC_HYGIENE.md`](../governance/DOC_HYGIENE.md)

Items listed below under "Layer B" and "Verification gaps" are **observations about repository
state**, not tickets. Each remains behind its named gate. Nothing here elevates a parked,
gated, or retired item into Queue 1.

---


**Date:** 2026-08-14 · **Repo:** `Perps12-oss/ai-command-center` · **Baseline:** `origin/main` (fetched)
**Mode:** read-only. No commits, branches, or `docs/` files created.

**Canon-integrity check:** the four authority documents read (`docs/governance/IMPLEMENTATION_GUIDE.md`,
`docs/governance/HISTORICAL_AND_RETIRED_WORK.md`, `docs/architecture/adr/README.md`, `docs/plans/README.md`)
are **byte-identical to `origin/main`** — `git diff origin/main -- docs/governance docs/architecture/adr/README.md docs/plans/README.md docs/audits` is empty. Quotes below are repository truth, not branch tips.

**Two layers, kept separate** (per `IMPLEMENTATION_GUIDE.md`: *"Do not invent replacement tickets from historical inventories"*):

- **Layer A — canonical:** what the Implementation Guide authorizes. Queue 1 is EMPTY.
- **Layer B — empirically incomplete on `main`, NOT authorized work:** verified code/doc gaps, each with its gate.

---

## Queue 1 (Must Do)

**EMPTY.** No approved implementation work is outstanding (`IMPLEMENTATION_GUIDE.md:208`).

| # | Item | Status |
|---|------|--------|
| 1 | Phase B remediation | ✅ COMPLETE on `main` (#105) |
| 2 | PHASE R1 — Runtime Reconciliation | ✅ COMPLETE (P1–P4; P5 closed via ADR-014 research-only) |
| 3 | State Authority / SA.mutate | ✅ COMPLETE — live mutate = WM + Memory + Goals; WEA outside (ADR-017) |
| 4 | Phase 5 — tiered EventBus pools | ❌ **REMOVED from Queue 1 — PARKED**, not "next" |

**Blockers:** none. Queue emptiness is intentional, not a stall.
**Standing process (not a ticket):** verification gates on `main` per `PHASE_COMPLETION_RULE.md`.

## Queue 2 (Evaluate)

Class B reference only. **No implementation authority.** Each needs Integration Proposal + Accepted ADR before code. All at status *not evaluated*.

| Item | Status | Blocker |
|------|--------|---------|
| Goose provider abstraction | Reference only | Stage 3 owner checkpoint (GATED) |
| Goose plugin discovery | Reference only | Stage 3 + Integration Proposal + ADR |
| Goose configuration patterns | Reference only | Stage 3 + Integration Proposal + ADR |
| Goose logging patterns | Reference only | Stage 3 + Integration Proposal + ADR |
| Goose desktop runtime | Reference only | Stage 3 + Integration Proposal + ADR |

Stage 3 framing is mandated: *"Which patterns strengthen the architecture we now have?"* — never *"How do we make ACC more like Goose?"*

## Queue 3 (Future)

Class C long-term backlog. Not started, not scheduled, no owner gate cleared.

| Item | Status |
|------|--------|
| Pattern registry | Backlog |
| Plugin marketplace | Backlog — needs new contracts (Program 4 gate) |
| Advanced runtime | Backlog |
| New UI ideas | Backlog |
| Performance | Backlog under `PERFORMANCE_CONSTITUTION.md` — does **not** authorize Phase 5 tiered pools |
| Platform hotkey / tray live wire | Phase 11 backlog; owner SKU decision GATED |

## Parked / Retired

### Retired architecture — do not re-wire without a *superseding* Accepted ADR

| Package | Binding ADR | Unpark condition |
|---------|-------------|------------------|
| OperatorKernel | ADR-006 (live intake = ExecutionAuthority) | ADR superseding 006 |
| GoalEngine | ADR-012 (live = GoalRepository + SingleGoalScheduler) | ADR superseding 012 |
| PlanningEngine | ADR-013 (live = PlannerService) | ADR superseding 013 |
| AgentCoordinator | ADR-013 (live = AgentRuntimeService) | ADR superseding 013 |
| PredictiveEngine | ADR-014 (research/unit-test tree only) | ADR superseding 014 |
| UndoReplay | ADR-014 (live = Timeline/Snapshot/WM recover) | ADR superseding 014 |

Code may still exist on disk. **Exists ≠ Wired ≠ Authoritative.**

### Abandoned programs

| Program | Live substitute |
|---------|-----------------|
| Chat C2–C4 modernization | AppState / `chat.*` path |
| Knowledge Federation as unified SoT / vectors | Vector DB constitutionally gated |
| Insights as unfinished product | UI placeholder is intentional empty state |
| Goose extras / `provider_sdk` live-wire | AppState provider snapshot |
| macOS hotkey Impl as current work | `get_hotkey_provider()` placeholder; `_start_tap()` log stub; SKU GATED |

### Parked ideas

| Idea | Unpark gate |
|------|-------------|
| EventBus pool isolation (Phase 5 tiered dispatch) | **Measured** single-queue contention + Performance Investigation Report + owner approval (Art. VII/XII) |
| ADR-008 derived compaction | Owner product decision; ADR-020 forbids memory SoT |
| Read-only `FederationService` | Owner; type exists, **not** in composition root |
| ADR-021 composed DecisionRecord on ordinary success/failure | Owner sequencing |
| ADR-022 threshold escalation | Owner; not Queue 1 |
| Semantic / vector memory | Constitutional amendment + UCGS profile |
| Remote plugin marketplace / distributed cloud execution | New contracts |

### Historical branch

`cursor/phase5-async-eventbus-744e` — **ABANDONED, not a merge candidate.** Conflicts with #170 backpressure; isolation tests would break single-queue FIFO. Explicitly *not* "incomplete awaiting merge."

## Proposed ADRs (non-binding)

Split by whether the gap is honesty debt or unimplemented scope.

### (a) Proposed but LIVE-IN-EFFECT — status-honesty debt, no code work

| ADR | Title | Note |
|-----|-------|------|
| 001 | Persistence Strategy | LIVE-IN-EFFECT |
| 002 | Scheduler Model | LIVE-IN-EFFECT |
| 003 | Observer Flow | LIVE-IN-EFFECT |
| 004 | Runtime Approval Model | LIVE-IN-EFFECT |
| 007b | Provider Registry | LIVE SNAPSHOT on AppState; Goose extras obsolete |
| 009 | Tool Confirmation Router | LIVE-IN-EFFECT; narrowed by ADR-018 |

Five of these remain formally Proposed while the code is live — flagged in the inventory as "Proposed, never decided."

### (b) Proposed and unimplemented — parked, not authority

| ADR | Title | Disposition |
|-----|-------|-------------|
| 008 | Conversation Compaction | UNDECIDED / PARKED; narrowed by ADR-020 |
| 010 | Modular Tool Inspection | PARKED / NOT REQUIRED |
| 011 | Telemetry Backends | PARKED / NOT REQUIRED |

### (c) Document rewrite owed

| ADR | Title | Disposition |
|-----|-------|-------------|
| 005 | World Model Authority | **SUPERSEDED / REWRITE REQUIRED** (by ADR-015–017) |

## Accepted ADRs pending Section 9 (implementation plan)

**Terminology:** in ADR-018–023, **§9 = Council Decision** and **§10 = Actionable Implementation Plan (M1–M5)**. The repo says "Section 9" for the whole council-decision→implementation program. Milestone gaps below are against **§10**.

Canon (`CLAUDE.md`): *"Section 9 of ADR-018–023 is Accepted architecture already on `main`. Remaining optional envelopes (ADR-021/022 extras) are PARKED, not Queue 1."*

| ADR | §10 milestones landed | Incomplete | Gate |
|-----|----------------------|-----------|------|
| 018 Tool Invocation | M1 intention contract, M2 schema validation, M3 arch-lint R5 bypass refusal (#161) | M4 — ADR-009 narrowing update PR | Follow-on; not Queue 1 |
| 019 Planning | M1–M3 (replan request w/ WM snapshot, topics, fail→replan) (#161) | M4 stuck detector — partially live at replan-stuck only | Not Queue 1 |
| 020 Memory | M1 memory boundary doc, M2 WM-first context | M3 (conditional on ADR-008), M4 doc pass | ADR-008 owner decision |
| 021 Explainability | M1 DecisionRecord + M4 TruthBoundary wired; core LIVE | **M2/M3 partial** — record not emitted on ordinary success/failure; M5 DecisionCard optional | **PARKED** — owner sequencing |
| 022 Confidence & Autonomy | M1 AutonomyScore; core LIVE | **M2/M3/M4 partial** — score not computed on ordinary paths; threshold escalation absent | **PARKED** — owner |
| 023 Model Strategy | M1 degrade-mode docs (#157) | M2 tier-map, M3 local-only replan, M4 model-selection telemetry | Not Queue 1 |

**Verified on `origin/main`:** `_publish_decision_and_autonomy` has exactly **two** call sites in `ai_command_center/services/execution_orchestrator_service.py` (lines 375, 702) — awaiting-approval and replan-stuck. Ordinary success/failure paths do **not** emit. ADR-021 M2–M4 / ADR-022 M2–M4 are genuinely partial.
**Verified:** no `local_only` / `local-only` test coverage anywhere in `tests/` → ADR-023 M3 unimplemented.

## Open PRs with incomplete work

| PR | Branch | State | What is pending |
|----|--------|-------|-----------------|
| **177** | `audit/agent-shell-falsification` | OPEN, MERGEABLE/CLEAN | Gates non-UI command execution, validates interpreter args, **tier-gated HITL per ADR-004/ADR-022 (Option C)**. 15 files, +875/−47. **No Constitutional Pre-Flight in the diff.** |
| **178** | `cursor/tool-tier-classification-4b28` | DRAFT | SecurityTier HITL at `TOOL_INVOKE` boundary (Option a). 21 files, +868/−37. **No Constitutional Pre-Flight in the diff.** |
| **179** | `cursor/vendor-cursor-skills-d598` | DRAFT, MERGEABLE/UNSTABLE | Vendors pytest/httpx/hallmark/theme-factory/ui-ux-pro-max skills. Tooling only; CI unstable. |
| **172** | `cursor/p1-closeout-drain-dupes-efe6` | DRAFT | EventBus drain-on-shutdown, duplicate consolidation, UCGS negative gate. = inventory **U8** (P1 deferred non-blockers). |
| **171** | `cursor/planned-work-backlog-audit-4b28` | OPEN | **Content already on `origin/main`** (`PLANNED_WORK_INVENTORY.md` + its pre-flight both present). PR is redundant — close it. |
| **163** | `cursor/repo-state-closeout-f30c` | OPEN since 2026-08-07 | Docs-only tip-truth closeout. `REPO_STATE_HYGIENE_DISPOSITION_2026-08-07.md` and its pre-flight are **NOT on main**. UCGS check FAILURE, never babysat. = inventory **U7**. |

### ⚠ #177 / #178 collide and may implement PARKED scope

Both edit the same six core files (`command_sandbox.py`, `control_plane.py`, `security_policy.py`, `tools.py`, `execution_authority_service.py`, `tool_executor_service.py`) and the same four test files, under two different options ("Option C" vs "Option a"). Canon lists ADR-022 as *"LIVE core; threshold escalate **PARKED** (not Queue 1)"* — and ADR-022 M3 is precisely "escalate to approval when aggregate < configurable threshold." A PR claiming ADR-022 authority for tier-gated HITL is implementing against parked scope with Queue 1 empty.

## Unmerged branches with code

25 remote branches carry commits not on `origin/main`. Excluding the 6 PR heads above:

### Genuinely pending / undisposed

| Branch | Ahead | Non-doc files | Assessment |
|--------|-------|---------------|------------|
| **`feature/planner-evolution-phase-c0-constitution`** | **218** | **511** | **Not in any fossil index.** Forked 2026-06-26, last commit 2026-07-10 (`openhands`), **453 commits behind main**. "ACC Planner Evolution Program — Phase C0" + Planner Architecture docs 10–19 + domain models. Predates ADR-013/019; superseded in substance by PlannerService. **Undocumented fossil — needs explicit disposition in `HISTORICAL_AND_RETIRED_WORK.md`.** |
| `cursor/section9-adr-followons-621d` | 2 | 27 | WM apply, TruthBoundary, confirmation, WM-first context. Substantially landed via #161; residual delta unverified. |
| `cursor/section9-handover-621d` | 1 | 0 | Docs-only handover for the next agent after #161. Never merged. |
| `devin/pr-ui-e01-universal-inspector` | local | — | PR-UI-E01 universal inspector; E-series landed on `main` per `HISTORICAL_AND_RETIRED_WORK.md`. Stale. |
| `devin/pr-ui-e04-navigation-shell` | local | — | PR-UI-E04 navigation shell. Same — E05–E13 landed; stale. |

### Landed elsewhere / superseded (no action but branch hygiene)

`cursor/phase5-async-eventbus-744e` (5 ahead, 8 non-doc — **complete code, no PR, GATED/ABANDONED**), `feat/receipt-boundary-phase-a` (7), `cursor/receipt-boundary-fail-closed-323d` (7), `cursor/p1-remediation-ucgs-efe6` (6), `cursor/runtime-integrity-closeout-4b28` (4), `cursor/stage2-edges-goals-inventory-6855` (2), `cursor/control-plane-security-audit-4b28` (2), `cursor/control-plane-security-remediation-4b28` (2), `cursor/tom-audit-sa-mutate-track-6855` (2, docs-only), `cursor/runtime-identity-loud-30d3` (1), `cursor/governance-alignment-323d` (1), `cursor/perf003-openai-settings-snapshot-30d3` (1), `cursor/perf004-navigation-show-view-30d3` (1), `cursor/b5-hero-ea-intake-323d` (1), `cursor/governance-audit-docs-323d` (1), `cursor/tom-auditor-v2-sync-30d3` (1, docs-only).

## Verification gaps

| # | Gap | Evidence |
|---|-----|----------|
| V1 | **Pre-flight written, implementation never landed** — `CONSTITUTIONAL_PRE_FLIGHT_REPO_STATE_CLOSEOUT.md` and `REPO_STATE_HYGIENE_DISPOSITION_2026-08-07.md` are absent from `origin/main`; both live only on PR #163, open 7 days with a UCGS FAILURE. |
| V2 | **Implementation without pre-flight** — neither PR #177 nor #178 includes a Constitutional Pre-Flight. `CLAUDE.md`: *"Implementation may not begin before pre-flight completion… Skipping it is a constitutional process failure even if CI is green."* Art. X. |
| V3 | **Duplicate implementation across #177/#178** on identical core files under conflicting options — Inv 11 (single source of truth) risk if both merge. |
| V4 | **PR #171 redundant** — its content is already on `main`; leaving it open means the tracking record disagrees with repository truth. |
| V5 | **Governance-layer fossils F-1/F-2 unfixed** — verified on `origin/main`: `ucgs.profiles/ai-command-center.yaml:87` still says *"Restore canonical UI → CommandRouter → Service flow"* (S4/CRITICAL) and `:111-112` describe the pre-ADR-006 pipeline. A CRITICAL rule instructing restoration of a retired architecture. Governance honesty, not product Queue 1. |
| V6 | **Zero GitHub issues** (0 open / 0 closed). All tracking lives in markdown that gets superseded — named in the inventory as *the* mechanism of work loss. |
| V7 | **PERF Art XV "Mitigated", not "Closed"** — PERF-001/002 need a Windows ARM64 GUI soak with Runtime + Perf inspectors open. Operator-owned; cannot be closed from a cloud/CI environment. |
| V8 | **`TOM_APPROVAL.lock` stale and unenforced** — hand-maintained, not CI-gated; `.cursor` hooks and `tom-audit.yml` are advisory only. Green CI ≠ approved. |
| V9 | **`feature/planner-evolution-phase-c0-constitution` has no disposition record** in `HISTORICAL_AND_RETIRED_WORK.md`, despite being the largest divergent branch in the repo. |

## Layer B — empirically incomplete on `main` (NOT authorized work)

Source: `docs/audits/PLANNED_WORK_INVENTORY.md`, which is itself banner-marked **HISTORICAL / SUPERSEDED — NOT AN IMPLEMENTATION QUEUE**, baselined at `b949f3e` (#170) on 2026-08-12. `main` has since taken #161/#175, so it is stale. Re-verification status noted per row.

| ID | Item | Re-verified on `origin/main` today? | Gate |
|----|------|--------------------------------------|------|
| U1 | Phase C living-doc honesty (C1–C4) | Not re-verified | None named — but Queue 1 empty |
| U2 | UCGS fossils F-1 / F-2 | ✅ **CONFIRMED OPEN** (yaml:87, :111–112) | None — governance honesty |
| U3 | Section 9 remainder G5 — DecisionRecord/AutonomyScore on ordinary paths | ✅ **CONFIRMED OPEN** (2 emit sites only) | **PARKED** — owner sequencing (ADR-021/022) |
| U4 | ADR-023 M3–M4 | ✅ **CONFIRMED OPEN** (no `local_only` tests) | Not Queue 1 |
| U5 | ADR-008 compaction (narrowed) | ✅ **CONFIRMED OPEN** (no compaction topics) | Owner product decision |
| U6 | UI library drop-to-canvas | ⚠ Partial — `_on_drag` is `pass` at `node_library_palette.py:142`; also a name collision at `:91` vs `:138`. "(0,0)" claim not located | None named |
| U7 | PR #163 stale closeout | ✅ CONFIRMED (open, content off main) | None — revive or close |
| U8 | P1 deferred non-blockers | ✅ CONFIRMED (PR #172 draft) | None — explicitly non-P1 |
| U9 | N-2 outcome-gated launch timeline | Not re-verified | Deferred from #167 |
| U10 | Governance audit follow-ons | Not re-verified | None named |
| U11 | Optional R1 cleanup | Asserted by stop-line; not re-verified | Most items need a **new ADR** extending 015/016/017 |
| U12 | PERF soak | ✅ CONFIRMED operator-owned | Windows ARM64 hardware; cannot close from cloud |

Rows marked "not re-verified" are asserted by a superseded inventory, not by today's code reading.

## Summary

**Canonical (Implementation Guide authority):**

| Metric | Count |
|--------|-------|
| **Queue 1 planned work** | **0** — EMPTY |
| Queue 1 completed (do not re-open) | 3 |
| Queue 2 (evaluate, reference only) | 5 themes, 0 implemented |
| Queue 3 (future backlog) | 6 themes, 0 started |
| Blocked / hard-stopped | 7 named hard stops |
| Parked ideas | 7 |
| Retired packages | 6 |
| Abandoned programs | 5 |

**Non-canonical incomplete (verified, NOT authorized):**

| Metric | Count |
|--------|-------|
| Empirically incomplete items (U1–U12) | 12 — **7 confirmed open today**, 1 partial, 4 not re-verified |
| Accepted ADRs with partial §10 milestones | 6 (018–023); 2 of them (021, 022) explicitly PARKED |
| Proposed ADRs live-in-effect (honesty debt) | 6 |
| Proposed ADRs unimplemented / parked | 3 |
| ADRs needing rewrite | 1 (ADR-005) |
| Open PRs | 6 — 2 redundant/stale, 2 colliding without pre-flight, 1 tooling, 1 non-blocker |
| Unmerged branches with commits | 25 — 1 major undisposed (218 ahead), 4 pending, 20 superseded |
| Verification gaps | 9 |

**Bottom line.** Nothing is authorized and waiting. The repo has deliberately emptied Queue 1 and converted almost every historical "unfinished" item into RETIRED (superseded by Accepted ADR), PARKED (named owner gate), or ABANDONED (program-level). Real outstanding work is process debt, not feature debt: two colliding open PRs implementing tier-gated HITL against parked ADR-022 scope with no Constitutional Pre-Flight; a 218-commit branch with no disposition record; UCGS CRITICAL rules that instruct restoring a retired architecture; and a tracking system (markdown, zero GitHub issues) that the repo's own audit names as the mechanism by which work gets lost.

**Recommended next actions (owner decisions, not implementation):**
1. Resolve #177 vs #178 — pick one option, require a Constitutional Pre-Flight, confirm it does not implement parked ADR-022 M3.
2. Close #171 (already on `main`); revive-or-close #163.
3. Add `feature/planner-evolution-phase-c0-constitution` to `HISTORICAL_AND_RETIRED_WORK.md` with an explicit disposition.
4. Decide whether UCGS F-1/F-2 honesty is authorized as a governance-config fix (it touches no product code).
