# Planned Work Inventory — Unimplemented, Gated, Retired, and Lost to Scope Creep

**STATUS:** HISTORICAL / SUPERSEDED — **NOT AN IMPLEMENTATION QUEUE**

**HISTORICAL / NON-AUTHORITATIVE**

This document records a 2026-08-12 inventory. It is **not** the current implementation plan.  
**Do not implement from this document.**

Canonical planned-work queue: [`docs/governance/IMPLEMENTATION_GUIDE.md`](../governance/IMPLEMENTATION_GUIDE.md) (Queue 1 is **EMPTY**).  
Fossil index: [`docs/governance/HISTORICAL_AND_RETIRED_WORK.md`](../governance/HISTORICAL_AND_RETIRED_WORK.md)  
Disposition: [`docs/audits/FOSSIL_DISPOSITION_AUDIT.md`](FOSSIL_DISPOSITION_AUDIT.md)

The “UNGATED / what is actually next” tables below are **superseded**. They must not be treated as Queue 1. Phase 5 is **PARKED**, not gated-next. Retired packages are **ABANDONED** as live paths.

---

**Date:** 2026-08-12  
**Baseline:** `origin/main` @ `b949f3e` (PR #170)  
**Authority:** `PROJECT_CONSTITUTION_V4.md`; `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`; `docs/audits/R1_UNGATED_STOP_LINE.md`  
**Pre-flight:** `docs/audits/CONSTITUTIONAL_PRE_FLIGHT_PLANNED_WORK_INVENTORY.md`  
**Rule:** Exists ≠ Wired ≠ Authoritative. A plan header is not proof. A feature branch is not `main`.

This is an inventory, not a completion claim and not an implementation plan.
Do not start gated items from this document.

---

## Executive summary

Most of the 2026 roadmap is **not unfinished in the naive sense**. Large
subsystems were **built, then retired from the live path by Accepted ADRs**,
or **parked behind hard stops**. The work that actually got lost is narrower:

1. **Fully coded, never merged** — Phase 5 Async EventBus on
   `cursor/phase5-async-eventbus-744e` (no PR).
2. **Seeded, never started** — Phase C docs↔code reconciliation and UCGS
   fossils F-1 / F-2.
3. **Explicitly deferred, then displaced** — Section 9 remaining milestones
   (DecisionRecord / AutonomyScore on ordinary success/failure), receipt
   follow-ons N-2, P1 shutdown drain.
4. **Proposed, never decided** — Goose ADRs 007b / 008 / 010 / 011 and
   Brain ADRs 001–005 still marked Proposed while much of 001/002/004/005
   is already live.
5. **Stale living docs** — `MASTER_ROADMAP_2026.md` last revised 2026-07-11
   still describes OperatorKernel as the critical path. Agents who plan from
   it will re-lose work.

GitHub **issues are unused** (zero open, zero closed). Tracking lives in
markdown that gets superseded. That is the main mechanism of loss.

---

## How to read the tables

| Class | Meaning | Action |
|-------|---------|--------|
| **UNGATED** | Approved, incomplete, no hard stop | Eligible next work |
| **GATED** | Hard stop named in `R1_UNGATED_STOP_LINE.md` or PERFORMANCE_CONSTITUTION | Do not implement |
| **RETIRED** | Accepted ADR took it off the live path | Do not re-wire without a superseding ADR |
| **PROPOSED** | ADR / INT not Accepted | Do not implement as if binding |
| **BACKLOG** | Planned, never started or never finished | Recorded; not current Queue 1 unless listed UNGATED |
| **LOST** | Started or finished off-`main`, then displaced | Recover, close, or explicitly abandon |
| **STALE DOC** | Document disagrees with code on `main` | Honesty pass; do not plan from it |

---

## 1. What is actually next (UNGATED)

These are incomplete on `main` and are **not** behind a named hard stop.

| ID | Item | Evidence on `main` | Notes |
|----|------|--------------------|-------|
| U1 | **Phase C — living-doc honesty** | `HANDOVER_PHASE_A_B_TO_CURSOR.md` §5: Phase C **NOT STARTED** | Original C1–C4: Phase 7 roadmap honesty, Phase 5 async waiver text, Phase 8/10 hygiene, ADR-007/009/011 status. Still open after A/B/B5/P1. |
| U2 | **UCGS fossils F-1 / F-2** | `PHASE_C_BACKLOG_GOVERNANCE_FOSSILS.md` | `pipeline.canonical` still names CommandRouter as intake; `eventbus_bypass.remediation` tells engineers to restore that retired flow. Systematic pass, not opportunistic one-liners. |
| U3 | **Section 9 remainder — G5** | `_publish_decision_and_autonomy` only at awaiting-approval and replan-stuck (`execution_orchestrator_service.py`) | ADR-021 M2–M4 / ADR-022 M2–M4: DecisionRecord + AutonomyScore are **not** emitted on ordinary success or ordinary failure. Domain + UI card exist. |
| U4 | **ADR-023 M3–M4** | Degrade-mode docs exist (`MODEL_ORCHESTRATION.md`); local-only replan / telemetry-never-gates-cloud tests incomplete vs plan | M1 docs landed in #157. |
| U5 | **ADR-008 compaction (narrowed)** | No `conversation.compaction_*` topics; ContextManager still truncates | Binding only as **derived view** (ADR-020). Not a memory SoT. Still unimplemented as a product feature. |
| U6 | **UI library drop-to-canvas** | `UI_REFURBISHMENT_BACKLOG.md` P3 uncompleted; `node_library_palette.py` `_on_drag_start` adds at `(0,0)` | Last open item of the 15-PR UI refurbishment program. |
| U7 | **PR #163 stale closeout** | Open since 2026-08-07; UCGS check **FAILURE**; never babysat | Docs-only tip-truth. Either revive against current `main` or close as superseded by later honesty commits. |
| U8 | **P1 deferred (non-blocker)** | `P1_FINAL_REMEDIATION_REPORT.md` | EventBus full drain-on-shutdown; broad duplicate-implementation purge. Not P1. |
| U9 | **N-2 outcome-gated launch timeline** | `RECEIPT_FAIL_CLOSED_REPAIR_CHANGE_NOTE.md` | Explicitly deferred from #167. |
| U10 | **Governance audit follow-ons** | `ACC_GOVERNANCE_AUDIT.md` §Recommended follow-ons | Stale “warn mode” wording; hook vs pre-commit alignment; `.windsurf` UI constitution duplicate; `CURSOR_AUDIT_GATE.md` Devin-only language; stale `TOM_APPROVAL.lock`. |
| U11 | **Optional R1 cleanup** | `R1_UNGATED_STOP_LINE.md` optional list | GoalEngine schema/package cleanup; research-tree deletes; Memory **delete** via SA (needs ADR extending 015); Goals **lifecycle** via SA (needs ADR extending 016); read-only SA projection of WEA (needs new ADR). Cleanup without new ADR is the schema/tree deletes only. |
| U12 | **PERF soak (operator-owned)** | Tom PERF-001/002 closeout: Art XV **Mitigated**, not Closed | Win ARM64 GUI soak with Runtime + Perf inspectors open. Cloud cannot close this. |

**Not in this list:** Phase 5 Async EventBus (GATED — even though a complete
branch exists). Predictive/Undo live-wire (RETIRED). OperatorKernel re-wire
(RETIRED). Goose integration (GATED Stage 3).

---

## 2. Hard stops (GATED) — do not implement from this audit

From `docs/audits/R1_UNGATED_STOP_LINE.md` and `IMPLEMENTATION_GUIDE.md`:

| Work | Gate |
|------|------|
| Phase 5 Async EventBus (`tiered_dispatch_policy.py` / `async_dispatch_queue.py` on live `EventBus`) | Performance Investigation Report **and** human approval |
| Goose / external patterns as implementation | Stage 3 + Integration Proposal + Accepted ADR |
| Live-wire PredictiveEngine / UndoReplay | ADR **superseding** ADR-014 |
| Re-wire OperatorKernel / GoalEngine / PlanningEngine / AgentCoordinator | ADR **superseding** 006 / 012 / 013 |
| Platform hotkey/tray live wire | Phase 11 / plan dependency |
| Semantic / vector memory | Constitutional amendment + UCGS profile (Knowledge Federation plan) |
| Remote plugin marketplace / distributed cloud execution | New contracts (Program 4 gate status) |

---

## 3. Lost to scope creep (the displacement list)

These items were planned or started, then **other tracks consumed the
implementation role**. They are the answer to “what got lost.”

### L1 — Phase 5 Async EventBus: coded, never merged

| Fact | Evidence |
|------|----------|
| Plan status on `main` | `PHASE_5_ASYNC_EVENTBUS_PLAN.md` **PARTIAL**; truth matrix: policy only |
| Branch | `origin/cursor/phase5-async-eventbus-744e` |
| Commits vs `main` | `60c6bb3` policy+queue, `60b14fb` EventBus wire, `f7f446a`/`ef67a98` docs “complete”, `1b96fc8` merge #162 |
| Files | `async_dispatch_queue.py`, `tiered_dispatch_policy.py`, EventBus wiring, tests, `PERF_PHASE5_ASYNC_EVENTBUS_INVESTIGATION.md`, Tom audit |
| PR | **None** (`gh pr list --head` empty) |
| Why lost | Hard stop requires human approval. Work proceeded on a branch anyway, then PERF-001–004, Section 9, receipt boundary, and P1 landed on `main` instead. Branch was never opened as a PR, so babysit never ran. |

**Disposition:** Do **not** merge from this inventory. Treat as a recovery
candidate **after** owner approval. Rebase will be non-trivial (`main` has
moved through #163–#170, including EventBus delivery changes in #170).

### L2 — Phase C never started

After Phase A (receipt) + Phase B (intake) the handover seeded Phase C as
docs↔code reconciliation. Subsequent merged work: B5 Hero EA intake (#168),
receipt fail-closed (#167), P1 (#169/#170). Phase C files still say
**NOT STARTED**. Fossils F-1/F-2 remain in `ucgs.profiles/ai-command-center.yaml`.

### L3 — Section 9 “later PRs” deferred then skipped

`CONSTITUTIONAL_PRE_FLIGHT_SECTION9_FOLLOWONS.md` listed as out of scope:

- Full TruthBoundary / DecisionCard (021 M3–M5) — **partially landed** in the
  same PR (TruthBoundary in OrchestrationService; DecisionCard in ApprovalsView)
- WM-first context (020 M2) — **partially landed** (`ContextManager` comments
  and workspace-snippet priority)
- ADR-009 confirmation (018 M4) — **landed**
- Model tier differentiation tests (023 M2+) — **partial**

What did **not** land: G5 — DecisionRecord / AutonomyScore on normal
success and ordinary failure (only 2 call sites). After #157/#161 the
implementation role moved to PERF and P1.

### L4 — PR #163 left open

Docs closeout for Phase B roadmap + runtime authority. Open, UCGS failed,
Tom audit cancelled. Later honesty commits (#164/#165) and R1 docs may have
superseded parts of it. Never closed, never rebased.

### L5 — Goose Proposed ADRs parked

Expedition exp-001 produced PAT-001/003/004/006/007 → INT-001/005/007
“Approved for ADR” → **Proposed** ADR-007b, 008, 009, 010, 011.

| ADR | Title | Implementation on `main` |
|-----|-------|--------------------------|
| 007b | Provider Registry snapshot | `ProviderRegistry` + `ProviderRegistrySnapshot` exist; ADR still **Proposed**; Goose-style catalog topics incomplete |
| 008 | Conversation compaction | **Not implemented** (narrowed by ADR-020 to derived view) |
| 009 | Tool confirmation router | **Partial live** (Section 9; still Proposed) |
| 010 | Modular tool inspection pipeline | **Not implemented** (no `ToolInspectionService`) |
| 011 | Layered telemetry backends | **Not implemented** (no `TelemetryExporter`) |

Stage 3 + “research cannot create implementation work” correctly blocked
Goose-shaped code. The ADRs were never Accepted or Rejected, so they sit
in limbo while Section 9 / R1 / PERF ran.

### L6 — Research expeditions 002–013 never started

`research/backlog/repositories.md`: OpenHands, LibreChat, PyGPT, Logseq,
Obsidian, graph viz, CRDTs, VS Code, Ollama — all **Queued**. Only Goose
completed. Class C / Stage 3. Not lost accidentally; starved by the
single-implementation-role rule.

### L7 — Chat modernization C2–C4

`CHAT_MODERNIZATION_SPEC.md` C0 exists. Package `ui/views/chat/` exists
(C1-ish). `chat_view.py` is still **877 LOC** (target &lt;600). Spec
acceptance checkboxes for C2 are unchecked. Phase B E00–E13 and later
workspace hardening ran instead.

### L8 — Knowledge federation (Phase 8b)

`PHASE_8_KNOWLEDGE_FEDERATION_PLAN.md` **NOT_COMPLETE**. Missing
`knowledge_query_service.py`, `knowledge_index_service.py`, unified
`knowledge.*` topics, vector search (constitutionally gated). Federation
service + World Explorer graph exist; the plan’s query API does not.

### L9 — Cross-platform (roadmap Phase 11)

`PHASE_9_CROSS_PLATFORM_PLAN.md` **NOT_COMPLETE**. `get_hotkey_provider()`
still returns a placeholder; `platform/macos|linux/` Impl packages are
unwired. `platform_service.py` is a wall of `NotImplementedError` for
tray/notifications/window/clipboard. `ui/tray.TrayController` exists
separately. Roadmap said this could run **in parallel** after Phase 5;
it never did.

### L10 — Insights analytics

E13 shipped a **placeholder by plan**. No follow-on for an analytics
engine was scheduled after Phase B closed (#105). `InsightsView` still
projects empty-state copy.

### L11 — `provider_sdk/` dormant (O-3)

Package exists (`adapters.py`, `lifecycle.py`, `receipts.py`, …). Owner
decision O-3: do not wire. Paper stack alongside live
`providers/provider_registry.py`. Easy to mistake for a live path.

### L12 — Phase 8 `gemini_adapter.py`

Operator Kernel plan listed Gemini adapter. File **absent**. Kernel itself
is RETIRED from live (ADR-006), so this is research-tree incompleteness,
not a product hole — unless someone plans from `PHASE_8_OPERATOR_KERNEL_PLAN.md`.

### L13 — Historical unmerged branches (2026-07 inventory)

`REPOSITORY_TRUTH_AUDIT.md` (historical) listed orphans:
`phase-12-state-intelligence` (PR #81 park), plugin-catalog, planner-evolution,
reasoning-loop, program4-slice4, phase7-ari-update. Those were already
stale in July. They are a prior generation of the same failure mode:
work started on branches, then a newer program became the queue.

### L14 — Tracking medium

**Zero GitHub issues.** Backlogs are markdown files. When a new program
opens (R1, Section 9, PERF, P1), previous markdown is not converted into
a durable queue. `MASTER_ROADMAP_2026.md` is still titled ACTIVE with a
2026-07-11 revision history.

---

## 4. Planned but never finished (BACKLOG by phase)

Code-verified 2026-07-20 in `PHASE_PLANS_ARCHIVE_VERIFICATION.md`;
re-checked against `b949f3e` for this audit. **Zero Phase 5–10 plans are
COMPLETE_ON_MAIN.**

| Plan | Code status | What is missing vs the plan | Class |
|------|-------------|-----------------------------|-------|
| Phase 5 Async EventBus | PARTIAL | `tiered_dispatch_policy.py`, `async_dispatch_queue.py` **not on main**; R4c/R4d isolation; &lt;50ms gate evidence | GATED + LOST (branch) |
| Phase 6 External Capability Bridge | PARTIAL | Bridge **wired**; directory MCP scan / named `runtime/mcp_runtime_provider.py` incomplete vs plan text | BACKLOG |
| Phase 7 Multi-Agent Runtime | SUPERSEDED | Archived; do not implement | RETIRED layout |
| Phase 8 Operator Kernel | PARTIAL / research | Kernel **not** in `service_factory`; no live model-agnostic intake | RETIRED live (ADR-006) |
| Phase 8b Knowledge Federation | NOT_COMPLETE | Query/index services, `knowledge.*` topics, vectors (amendment) | BACKLOG / GATED (vectors) |
| Phase 9 Goals & Multi-Agent | PARTIAL / research | Live = GoalRepository + SingleGoalScheduler + PlannerService + AgentRuntimeService. GoalEngine / PlanningEngine / AgentCoordinator retired | RETIRED live (ADR-012/013) |
| Phase 9 Cross-Platform (roadmap 11) | NOT_COMPLETE | Hotkey getter placeholder; tray/notifications stubs | BACKLOG |
| Phase 10 World Model | PARTIAL | Core WM + SA mutate **live**; Predictive/Undo **retired** | RETIRED predictive (ADR-014) |
| UI Refurbishment follow-on | Almost done | Library palette drop-to-canvas | UNGATED U6 |
| Chat modernization | C0 + partial C1 | C2 AppState-only chat; C3 workspace card; C4 markdown v2 | BACKLOG |
| MSI packaging | Design + WiX/spec present | `PACKAGING_MSI_DESIGN.md` still says “implementation next”; roadmap marks P1 complete | STALE DOC / BACKLOG |
| VNext blueprint | North-star doc | Cognitive stack L4 “gap: PlannerService” is **stale** — PlannerService is live | STALE DOC |

---

## 5. Retired by Accepted ADR (not lost — decided)

Do not treat these as “unimplemented product.” They exist in tree for
tests/research. Re-wiring requires a **new** ADR.

| Component | ADR | Live substitute |
|-----------|-----|-----------------|
| OperatorKernel | 006 | ExecutionAuthority intake |
| GoalEngine | 012 Option A | GoalRepository + SingleGoalScheduler |
| PlanningEngine | 013 | PlannerService |
| AgentCoordinator | 013 | AgentRuntimeService |
| PredictiveEngine | 014 | Brain heuristics / SA-WM |
| UndoReplay package | 014 | TimelineService / SnapshotService / WM recover |
| Workflows / executions / agents `SA.mutate` | 017 | Remain outside SA |

Truth matrix: `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`.

---

## 6. Proposed ADRs — never Accepted (PROPOSED)

**Do not implement from these as if binding.**

| ADR | Title | Reality check |
|-----|-------|----------------|
| 001 | Persistence Strategy | SQLite + repositories **are** live; ADR never Accepted |
| 002 | Scheduler Model | `SingleGoalScheduler` **is** live; ADR never Accepted |
| 003 | Observer Flow | Observer framework docs exist; ADR never Accepted |
| 004 | Runtime Approval Model | READ / WRITE / WRITE_DESTROY **are** live; ADR never Accepted |
| 005 | World Model Authority | WM **is** SoT; ADR never Accepted |
| 007b | Provider Registry (Goose) | Partial code; ADR Proposed |
| 008 | Compaction | Narrowed by 020; unimplemented |
| 009 | Confirmation router | Partial live via Section 9; still Proposed |
| 010 | Tool inspection pipeline | Unimplemented |
| 011 | Telemetry backends | Unimplemented |

ADR-001–005 are **governance fossils**: the decision was enacted in code
without promoting the ADR to Accepted. That is Phase C C4 work.

Accepted and binding: 006, 007a (notification storms), 012–023.

---

## 7. Section 9 (ADR-018–023) milestone board

CLAUDE.md / governance audit: **Active program = Section 9 + performance.**

| ADR | Milestone | On `main`? |
|-----|-----------|:----------:|
| 018 | M1 Intention contract + PlanStep map | ✅ |
| 018 | M2 Validation before TOOL_INVOKE + failure topics | ✅ |
| 018 | M3 Exclusive TOOL_INVOKE publisher (arch lint R5) | ✅ #161 |
| 018 | M4 Confirmation keyed by `run_id:step_id` | ✅ |
| 019 | M1 Observation + WM apply path | ✅ |
| 019 | M2 `plan.replan.request/result` | ✅ |
| 019 | M3 Bounded fail→replan | ✅ |
| 019 | M4 Stuck similarity + escalate | ✅ |
| 020 | M1 Memory boundary doc | ✅ |
| 020 | M2 WM-first context builder | ⚠️ snippets prioritized; not a full WM snapshot assembler |
| 020 | M3–M4 ADR-008 derived-view / truncation narrative | ⚠️ docs only |
| 021 | M1 DecisionRecord domain + projection | ✅ |
| 021 | M2 Populate on execution steps | ❌ G5 — only approval + stuck |
| 021 | M3 Surface in Evidence / Approvals / Mission Control | ⚠️ DecisionCard on Approvals only |
| 021 | M4 TruthBoundary live in orchestration | ✅ |
| 021 | M5 DecisionCard ↔ pending approval | ✅ ApprovalsView |
| 022 | M1 AutonomyScore domain | ✅ |
| 022 | M2 Compute at orchestrator / Brain gates | ❌ same 2 call sites |
| 022 | M3 Escalate below threshold; never bypass WRITE_DESTROY | ⚠️ policy path exists; score unused on happy path |
| 022 | M4 Project into Decision Record / Approvals | ⚠️ partial |
| 023 | M1 Degrade-mode docs | ✅ |
| 023 | M2 `model_tier_map` without vendor branching | ⚠️ settings exist; extra tests vs plan incomplete |
| 023 | M3 Local-only replan / destroy | ⚠️ |
| 023 | M4 Telemetry records model; never gates on cloud | ⚠️ |

---

## 8. Performance track remainder

| Item | Status |
|------|--------|
| PERF-001 AppState `chat.chunk` coalesce | Fix landed; Art XV **Mitigated**; soak open |
| PERF-002 Inspector rebuild coalesce | Fix landed; S1 skip-path follow-on claimed in #154; soak open |
| PERF-003 OpenAI keyring off `settings.snapshot` | Landed #159 |
| PERF-004 Navigation `_show_view` Tk work | Landed #160 |
| Phase 5 async as a perf fix | **GATED** (and LOST on a branch) |
| Win ARM64 freeze soak | Operator-owned; Cloud cannot close |

---

## 9. Stale documents that hide unfinished work

| Document | Problem |
|----------|---------|
| `docs/MASTER_ROADMAP_2026.md` | ACTIVE; last revision 2026-07-11; Phase 8 still “Operator Kernel critical path”; E1 local warn vs current `enforcement_mode: block` |
| `docs/plans/IMPLEMENTATION_ORDER.md` | Banner says HISTORICAL/STALE; still recommends Phase 8 as critical path |
| `docs/architecture/VNEXT_STATE_DRIVEN_BLUEPRINT.md` | Lists PlannerService as a gap |
| `docs/architecture/PROGRAM4_GATE_STATUS.md` | Last assessed 2026-07-06; “next slice” includes ExternalCapabilityBridge scaffold (now wired) |
| `docs/architecture/UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md` | Status ACTIVE; gaps table still lists E02–E13 as remaining — **program complete on main (#105)** |
| `docs/architecture/UI_COMPONENT_SPECS/E13_INSIGHTS_PLACEHOLDER.md` | “pending merge” |
| `docs/audits/HANDOVER_PHASE_A_B_TO_CURSOR.md` | Says B5 open and “not on main”; B5 closed #168; A/B on main via #166 |
| `docs/architecture/PACKAGING_MSI_DESIGN.md` | “MSI build implementation next” vs roadmap P1 complete |
| Phase 8 / 9 / 10 plans | Keep active as PARTIAL (correct) but still read like product backlogs rather than research archives |

Phase C C1 is specifically: make these documents match `main` so the next
agent does not re-implement retired architecture.

---

## 10. What is complete (so it is not re-opened)

Do not “recover” these; they are on `main`.

- Programs 1–3; Program 4 slices 1–3; Program 5 Phases A–D (reasoning MVP)
- Phase B UI E00–E13 (#105) including Insights **placeholder**
- R1 P1–P4; P5 Predictive/Undo disposition (ADR-014)
- Stage 2 soft-shadow; SA.mutate track CLOSED (ADR-015/016/017)
- ADR-018–023 **Accepted** (council); first Section 9 slice + 018 M3 / 019 harden
- B5 Hero New Goal via ExecutionAuthority (#168)
- Receipt boundary + fail-closed (#166/#167)
- P1 UCGS range-diff, SQLite txn guard, ACTION_INVOKE, permission gate (#170)
- ExternalCapabilityBridge **wired** (scaffold; not full MCP product)

---

## 11. Recommended recovery order

No calendar estimates. Technical order only. **Do not start gated rows.**

1. **Phase C honesty pass (U1+U2)** — fix F-1/F-2; mark ADR-001–005/009
   status honestly; banner `MASTER_ROADMAP` as sequencing-historical;
   close or rebase PR #163. Prevents the next agent from planning
   OperatorKernel as intake.
2. **Section 9 remainder (U3, U4)** — DecisionRecord / AutonomyScore on
   ordinary completion and failure; ADR-023 local-only / telemetry tests.
3. **Owner decision on L1** — approve, rewrite, or abandon the Phase 5
   branch. Until then it stays GATED.
4. **Small UI leftover (U6)** — library drop-to-canvas, if still desired.
5. **Accept or reject Proposed Goose ADRs (L5)** — 007b / 008 / 010 / 011
   should become Accepted (narrowed), Rejected, or Superseded. Leaving them
   Proposed is how they stay lost.
6. Everything else stays BACKLOG / GATED / RETIRED as classified above.

---

## 12. Sources (Class A)

- `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`
- `docs/audits/R1_UNGATED_STOP_LINE.md`
- `docs/audits/PHASE_PLANS_ARCHIVE_VERIFICATION.md`
- `docs/audits/PHASE_C_BACKLOG_GOVERNANCE_FOSSILS.md`
- `docs/audits/HANDOVER_PHASE_A_B_TO_CURSOR.md`
- `docs/governance/IMPLEMENTATION_GUIDE.md`
- `docs/plans/README.md`
- `docs/architecture/adr/README.md`
- `origin/cursor/phase5-async-eventbus-744e` (unmerged)
- GitHub: issues empty; PRs #157–#170; open PR #163

---

## Revision

| Date | Change |
|------|--------|
| 2026-08-12 | Initial inventory at `b949f3e` |
