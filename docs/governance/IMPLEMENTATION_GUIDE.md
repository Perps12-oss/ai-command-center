# Implementation Guide

**Status:** ACTIVE — subordinate operational guide (living document)
**Authority:** **Derives its authority entirely from `PROJECT_CONSTITUTION_V4.md` and the accepted ADRs** (e.g. `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`). This guide is **not** an independent authority.
**Scope:** Operationalizes *how* implementation is carried out. It **introduces no new governing rules**; it only restates and applies rules already established by the Constitution, the ADRs, architecture contracts, and existing governance (`docs/governance/PHASE_COMPLETION_RULE.md`).
**Related:** `docs/plans/README.md`, `docs/governance/HISTORICAL_AND_RETIRED_WORK.md`, `docs/audits/FOSSIL_DISPOSITION_AUDIT.md`, `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`

> **Canonical planned-work document:** This file is the **only** canonical active planning authority (Queue 1). Historical roadmaps, phase plans, and inventories are evidence, not implementation queues.
>
> **Active program:** [`STRATEGIC_RUNTIME_PROGRAM.md`](STRATEGIC_RUNTIME_PROGRAM.md) — six streams + Cross-OS as the only remaining strategic gate. Phase 0 baseline: [`docs/audits/STRATEGIC_GAP_MATRIX.md`](../audits/STRATEGIC_GAP_MATRIX.md).
>
> **Precedence of this document:** If anything here ever conflicts with `PROJECT_CONSTITUTION_V4.md`, an **Accepted** ADR, an architecture contract, or `PHASE_COMPLETION_RULE.md`, the higher-authority document always prevails and this guide is corrected. Changes to the underlying governance are made in those documents, not here. Historical roadmaps do not outrank this queue.

---

## Implementation Agent

This guide applies to any implementation agent (human or AI) working on ACC. The active implementation agent may change over time without affecting repository governance. All implementation agents are expected to follow the Project Constitution, approved ADRs, architecture contracts, implementation plans, and this implementation guide.

The identity of the implementation agent is not architecturally significant. Compliance with repository governance is. The repository—not any particular tool—is the long-term source of authority. The active implementation agent may be Devin, Cursor, Claude Code, Gemini CLI, or any other approved implementation tool; switching tools must not require governance changes.

Non-Cursor implementation agents: see root [`CLAUDE.md`](../../CLAUDE.md) for tool-parity procedures (babysit-PR intent, verification order, markdown-only rules). Governance inventory: [`docs/audits/ACC_GOVERNANCE_AUDIT.md`](../audits/ACC_GOVERNANCE_AUDIT.md).

---

## Purpose

ACC's development has moved from **multiple agents making overlapping implementation decisions** to **one implementation role consuming evidence from multiple sources**. This mirrors ACC's own architecture: **separate discovery from execution**.

This guide describes how that single implementation role executes work under existing governance. There is one place where implementation is *carried out*; **decisions about architecture, governance, and roadmap remain owned by the Constitution, the ADRs, and the project owner.**

```text
                    Research
              (Engineering Intelligence)
                       │
                       ▼
                 Goose Expedition
                       │
                       ▼
                  Pattern Reports
                       ▲
                       │
 Repository Truth ──► Implementation Agent ◄── Architecture
     (Tom Audit)                                (ADR / Constitution)
                       │
                       ▼
              Implementation Plan
                       │
                       ▼
                 Code Changes
                       │
                       ▼
                 Verification
```

---

## The implementation role

The active implementation agent acts as the **implementation role** — an executor, not an authority. Everything else is an evidence source.

### The role carries out
- Establishing repository truth (what actually exists / is wired on `origin/main`)
- Implementation planning
- Code changes and refactoring
- Testing, integration, verification
- Documentation updates **after** implementation

### The role does NOT decide
- Architecture decisions
- Roadmap reprioritization
- Research conclusions
- Pattern approval
- Constitution changes

Those arrive as **inputs** from their owning authorities. The implementation agent may surface them as proposals; it may not enact them unilaterally.

---

## Authority order (restated from Article II — not created)

Article II of `PROJECT_CONSTITUTION_V4.md` is the constitutional hierarchy. This guide **does not** amend Article II and **must not** invent alternate Level labels.

| Art II level | Source |
|--------------|--------|
| 1 | `PROJECT_CONSTITUTION_V4.md` |
| 2 | `AGENTS.md`, `docs/ARCHITECTURE_ENFORCEMENT.md` |
| 3 | `docs/ARCHITECTURE.md`, `ai_command_center/core/contracts.py`, `ai_command_center/core/events/topics.py` |
| 4 | Phase documents (gate history in `docs/ARCHITECTURE.md`) |
| 5 | Verification framework |
| 6 | Implementation |

### Binding subordinate decisions (not Art II Level 2)

- **Accepted ADRs** are **binding subordinate architectural decisions under V4**. Implementers must follow them. They are **not** Article II Level 2 and do **not** amend V4 unless Art XIV is followed.
- **Proposed ADRs** are **non-binding** (intent undecided). Do not implement from them as if Accepted.
- **Peer domain constitutions** (`PERFORMANCE_CONSTITUTION.md`, `docs/UI_CONSTITUTION.md`) govern their domains under V4; on conflict, **V4 wins**. They are not listed in Article II and are not elevated by this guide.
- **Roadmap / plans / repository truth / research / external repos** inform work in that operational order; none override V4 or Accepted ADRs. Research remains descriptive.

> **Applying the existing rule:** lower sources may *inform* higher ones but may not *override* them. **Information may flow upward as evidence; authority never flows downward.** An external repo may never silently change ACC's direction.
>
> `PHASE_COMPLETION_RULE.md` ("main is the only truth") governs *when a phase may be called complete*; audited code on `origin/main` is authoritative for that judgement. It does not subordinate the Constitution.
>
> **When authoritative sources conflict, implementation must stop until the conflict is resolved; the implementation agent must never resolve authority conflicts by assumption.**

---

## How to Read This Repository (document authority)

This section does **not** amend Article II. It tells a fresh engineer or LLM which documents win when they **conflict about what to implement next**.

Constitutional hierarchy (Article II) always wins. Accepted ADRs are binding subordinate decisions under V4; they are **not** Art II Level 2.

**DOCUMENT AUTHORITY (planned work / fossils)**

1. **Live code on `origin/main`** — Exists ≠ Wired ≠ Authoritative; the **live path** wins.
2. **`PROJECT_CONSTITUTION_V4.md`** — supreme (Art II Level 1).
3. **Accepted ADRs** — binding under V4. **Proposed ADRs are not implementation authority.**
4. **This Implementation Guide** — the **only** canonical planned-work queue (Queue 1 below).
5. **Current disposition / fossil index** — [`HISTORICAL_AND_RETIRED_WORK.md`](HISTORICAL_AND_RETIRED_WORK.md) and [`FOSSIL_DISPOSITION_AUDIT.md`](../audits/FOSSIL_DISPOSITION_AUDIT.md).
6. **Historical / research documents** — audits, old plans, retired packages, Proposed ADRs, `MASTER_ROADMAP_2026.md`, `PLANNED_WORK_INVENTORY.md`. Provenance only.

Historical plans, retired packages, Proposed ADRs, research branches, and old inventories are **not** implementation authority.

```text
                    CURRENT MAIN
                         │
                         ▼
                CURRENT ARCHITECTURE
                         │
                         ▼
                ACCEPTED DECISIONS
                         │
                         ▼
              THIS CANONICAL PLAN
                         │
                         ▼
                ACTIVE QUEUE 1
                         │
                         ▼
              IMPLEMENTATION WORK
```

---

## Current State (what is already on `main`)

Do not describe these as future work:

- **EventBus:** `async_dispatch=True` **single** `event-dispatch` queue (R4b). Not multi-pool.
- **Intake:** ExecutionAuthority (ADR-006). OperatorKernel is **not** live.
- **Receipts / TruthBoundary / HITL confirmation:** live (control-plane path repaired #175; closeout `docs/audits/RUNTIME_INTEGRITY_CLOSEOUT.md`).
- **Scheduler:** `SingleGoalScheduler`. GoalEngine is **not** live.
- **World Model + SA mutate:** ADR-015/016 live; workflows/executions/agents **remain outside** (ADR-017).
- **Chat:** AppState / `chat.*` path.
- **Provider catalog:** `AppState.provider_registry` snapshot.
- **Phase B, PHASE R1, SA.mutate track:** COMPLETE.

Retired packages (OperatorKernel, GoalEngine, PlanningEngine, AgentCoordinator, PredictiveEngine, UndoReplay) may still exist on disk. They are **RETIRED / NON-CANONICAL**. See [`HISTORICAL_AND_RETIRED_WORK.md`](HISTORICAL_AND_RETIRED_WORK.md).

---

## Decision process (before touching any code)

An operational checklist for applying the authority order above:

```text
Does repository truth / an approved plan already require this?
   └─ YES → Implement.
   └─ NO ↓

Does the Constitution, an **Accepted** ADR, or an architecture contract approve it?
   └─ YES → Implement.
   └─ NO ↓

Is this a major architecture change (planning, tool invocation, memory SoT,
autonomy, model coupling, dual authority, or “more like a generic AI agent”)?
   └─ YES → Run docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md
            (multi-council ADR). Do NOT implement until Council Decision
            Accept / Hybrid and Section 9 plan exist.
   └─ NO ↓

Does research recommend it?
   └─ YES → Create an Integration Proposal (for ADR / owner review). Do NOT implement.
   └─ NO ↓

Ignore / Defer.
```

This prevents **research creep** and **external-project creep**.

**Architecture Decision Framework:** Major architecture changes must survive structured opposition (Architect, Red Team, Alternative, Systems Board, Constitution Guardian) before an ADR is Accepted and before Section 9 implementation begins. See [`ARCHITECTURE_DECISION_FRAMEWORK.md`](ARCHITECTURE_DECISION_FRAMEWORK.md) and the ADR index [`docs/architecture/adr/README.md`](../architecture/adr/README.md).

---

## Evidence classes

Incoming information is triaged into three classes:

- **Class A — Repository Truth (Authoritative):** comes from the repo; the implementation agent trusts it. (e.g. Phase B CONDITIONS cleared on `main` (#105); Stage 2 soft-shadow + R1 P1–P4 + ADR-014–017 on `main`; SA.mutate track **CLOSED**; R4b single-queue EventBus **live**; OperatorKernel / Predictive / Undo **retired from live**.) Stream **code** for A–F is Class A only after Gates 2–3.
- **Class B — Engineering Intelligence (Reference):** e.g. Goose expedition notes. Reference material, **not** implementation instructions. Goose **code** is Stream F after Gate 2 Adopt/Adapt only.
- **Class C — Future Opportunities (Backlog):** Cross-OS (Stream G) remains the **only remaining strategic gate**. Other parked product ideas: see [`HISTORICAL_AND_RETIRED_WORK.md`](HISTORICAL_AND_RETIRED_WORK.md).

---

## The three queues

### Queue 1 — Must Do (blocks progress; from repository truth + approved plans)

**Queue 1: ACC Strategic Runtime & Architecture Completion Program** — [`STRATEGIC_RUNTIME_PROGRAM.md`](STRATEGIC_RUNTIME_PROGRAM.md).

This is owner-authorized. Do **not** invent extra tickets from historical inventories. Do **not** start stream **code** until that stream has Gate 2 ACCEPT (or remaining Section 9 confirmation) **and** Gate 3 Section 9 plan.

| Wave | Work | Status |
|------|------|--------|
| 0 | Strategic Gap Matrix | Deliverable in [`docs/audits/STRATEGIC_GAP_MATRIX.md`](../audits/STRATEGIC_GAP_MATRIX.md). **COMPLETE only after merge to `main`.** |
| 1 | Architecture closure (Gate 1–2) | Gate 1 drafts in [`docs/architecture/proposals/`](../architecture/proposals/). **No code.** Owner Gate 2 next. |
| 2–5 | Runtime foundations → capability → Goose hardening → full-system verification | **Blocked** until Gates 2–3 per stream. |
| 6 | Cross-OS (Stream G) | **Not opened.** Only remaining strategic gate. |

Streams A–F (explainability, autonomy, model strategy, EventBus, knowledge, Goose) move through: Integration Proposal → ADR Decision → Section 9 → Implementation → Verification → Close-out. “Gated” means a checkpoint, not indefinite parking.

**macOS Hotkey** as a standalone strategic item is **dropped** (Stream X).

Completed (do not re-open):

1. **Phase B remediation** — ✅ **COMPLETE** on `main` ([#105](https://github.com/Perps12-oss/ai-command-center/pull/105)).
2. **PHASE R1 — Runtime Reconciliation** — ✅ **COMPLETE**. P1–P4 passed; P5 Predictive/Undo disposition closed (ADR-014 research-only).
3. **State Authority / SA.mutate** — ✅ **COMPLETE**. Live mutate = WM + Memory + Goals; workflows/executions/agents remain outside (ADR-017).

Historical EventBus pool **branch** `cursor/phase5-async-eventbus-744e` remains **ABANDONED** (not a merge candidate). Stream D Stage 1 is measurement; do not resurrect that branch. Current main is R4b **single-queue** `async_dispatch=True`.

Standing process: verification gates on `main` per `PHASE_COMPLETION_RULE.md`.

> Historical inventory (superseded as a queue): [`PLANNED_WORK_INVENTORY.md`](../audits/PLANNED_WORK_INVENTORY.md). Do not implement from it.

### Queue 2 — Evaluate (subsumed)

Goose / external pattern **evaluation** is **Stream F** inside Queue 1’s program (Gate 1 IP-F). Class B notes remain reference-only until Gate 2 Adopt/Adapt.

### Queue 3 — Future (long-term backlog; Class C)

Pattern registry, plugin marketplace, advanced runtime, new UI ideas. **Cross-OS (Stream G)** is the only remaining **strategic** gate — last wave, separate effort envelope. Standalone macOS hotkey is **not** in this queue.

---

## Immediate roadmap

1. **Stage 1 — Stabilization:** ✅ **COMPLETE** on `main` (#105). R1 P2 wire-or-retire **closed** (ADR-006/012/013/014).
2. **Stage 2 — State Authority / R1 closeout:** ✅ **COMPLETE**. SA.mutate track CLOSED (`R1_UNGATED_STOP_LINE.md`). Predictive/Undo remain retired until an ADR superseding 014.
3. **Strategic Runtime Program (current):** Wave 0–1 documentation; then Gates 2–3; then stream implementation in dependency order. Goose question remains *"Which patterns strengthen the architecture we now have?"* — never *"How do we make ACC more like Goose?"* Cross-OS stays last.

---

## Change control (restated boundary)

These boundaries restate existing governance; they do not create new constitutional rules:

- Research **cannot** directly create implementation work.
- External repositories **cannot** directly change the roadmap.
- Every new architectural idea requires: (1) Integration Proposal, (2) Architecture approval (ADR if applicable — **multi-council framework** when major), (3) Implementation plan (ADR Section 9 after Council Decision), (4) Verification.

---

## Maintenance

This is a **living operational guide**, kept in sync with its authorities. The active implementation agent updates it when repository truth changes (new audit / merge to `main`), an ADR is accepted, the roadmap is re-sequenced by the owner, or a queue item lands. It never amends the Constitution, an ADR, or `PHASE_COMPLETION_RULE.md`; governance changes are made in those documents, and this guide follows.
