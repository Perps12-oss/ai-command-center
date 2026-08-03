# Implementation Guide

**Status:** ACTIVE — subordinate operational guide (living document)
**Authority:** **Derives its authority entirely from `PROJECT_CONSTITUTION_V4.md` and the accepted ADRs** (e.g. `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`). This guide is **not** an independent authority.
**Scope:** Operationalizes *how* implementation is carried out. It **introduces no new governing rules**; it only restates and applies rules already established by the Constitution, the ADRs, architecture contracts, and existing governance (`docs/governance/PHASE_COMPLETION_RULE.md`).
**Related:** `docs/plans/README.md`, `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md`, `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`

> **Precedence of this document:** If anything here ever conflicts with `PROJECT_CONSTITUTION_V4.md`, an approved ADR, an architecture contract, a canonical roadmap / approved implementation plan, or `PHASE_COMPLETION_RULE.md`, the higher-authority document always prevails and this guide is corrected. Changes to the underlying governance are made in those documents, not here.

---

## Implementation Agent

This guide applies to any implementation agent (human or AI) working on ACC. The active implementation agent may change over time without affecting repository governance. All implementation agents are expected to follow the Project Constitution, approved ADRs, architecture contracts, implementation plans, and this implementation guide.

The identity of the implementation agent is not architecturally significant. Compliance with repository governance is. The repository—not any particular tool—is the long-term source of authority. The active implementation agent may be Devin, Cursor, Claude Code, Gemini CLI, or any other approved implementation tool; switching tools must not require governance changes.

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

## Authority order (restated, not created)

The order below **restates** the precedence already established by `PROJECT_CONSTITUTION_V4.md` and the ADRs so implementers have it in one place. It creates no new hierarchy. This guide derives its authority from, and never supersedes, levels 1–5.

| # | Source | Examples |
|---|--------|----------|
| 1 | **`PROJECT_CONSTITUTION_V4.md`** — supreme authority | plus peer constitutions `PERFORMANCE_CONSTITUTION.md`, `docs/UI_CONSTITUTION.md` |
| 2 | **ADRs** | `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`, etc. |
| 3 | **Architecture contracts** | e.g. `docs/architecture/STATE_AUTHORITY_CONTRACT.md`, `docs/ARCHITECTURE.md` |
| 4 | **Repository truth** — current implementation + verified audits on `origin/main` | `IMPLEMENTATION_TRUTH_MATRIX.md`, Tom audits, code on `main` |
| 5 | **Canonical roadmap / approved implementation plans** | `docs/MASTER_ROADMAP_2026.md`, `docs/plans/PHASE_*.md` (active, code-verified) |
| 6 | **Research (Engineering Intelligence)** | expedition / pattern reports |
| 7 | **External repositories** | Goose, OpenHands, CrewAI, etc. |

> **Applying the existing rule:** consistent with the Constitution and `PHASE_COMPLETION_RULE.md`, lower-precedence sources may *inform* higher-precedence ones but may not *override* them. **Information may flow upward as evidence, but authority never flows downward.** Research (6) may motivate a roadmap change (5) only via an accepted ADR (2) / owner decision; an external repo (7) may never silently change ACC's direction. This is a restatement of existing governance, not a new rule.
>
> Note: `PHASE_COMPLETION_RULE.md` ("main is the only truth") governs *when a phase may be called complete*; for that judgement, audited code on `origin/main` is authoritative. It does not subordinate the Constitution or ADRs, which remain supreme for *decisions*.
>
> **When authoritative sources conflict, implementation must stop until the conflict is resolved; the implementation agent must never resolve authority conflicts by assumption.**

---

## Decision process (before touching any code)

An operational checklist for applying the authority order above:

```text
Does repository truth / an approved plan already require this?
   └─ YES → Implement.
   └─ NO ↓

Does the Constitution, an ADR, or an architecture contract approve it?
   └─ YES → Implement.
   └─ NO ↓

Does research (6) recommend it?
   └─ YES → Create an Integration Proposal (for ADR / owner review). Do NOT implement.
   └─ NO ↓

Ignore / Defer.
```

This prevents **research creep** and **external-project creep**.

---

## Evidence classes

Incoming information is triaged into three classes:

- **Class A — Repository Truth (Authoritative):** comes from the repo; the implementation agent trusts it. (e.g. Phase B has four outstanding conditions; Phase 5 Async EventBus incomplete; Operator Kernel intentionally unwired; State Authority is the next architectural milestone.)
- **Class B — Engineering Intelligence (Reference):** e.g. Goose provider abstraction / extension system / runtime / desktop architecture. Reference material, **not** implementation instructions.
- **Class C — Future Opportunities (Backlog):** e.g. potential provider registry, plugin registry, runtime improvements. Backlog, **not** current work.

---

## The three queues

### Queue 1 — Must Do (blocks progress; from repository truth + approved plans)

Source: EPOCH A audit + `PHASE_R1_RUNTIME_RECONCILIATION.md`. Ordered:

1. **Phase B remediation (close program conditions):** ✅ **on `main`** via [#105](https://github.com/Perps12-oss/ai-command-center/pull/105) (`f03a4fa`, 2026-07-29). Phase B UI program CONDITIONS cleared.
2. **PHASE R1 — Runtime Reconciliation** (priority order: Runtime authority → Composition → State → UI → Features; no Priority N+1 before N's gate passes). P1 **passed**. P2 registry updated; PlanningEngine/AgentCoordinator still unwired; GoalEngine quarantined. **P3 Stage 2:** Slices 1–4 (query, planner, WM node+edge mutate, Goals quarantine + dual-path inventory).
3. **State Authority Contract** (R1 Priority 3) — `docs/architecture/STATE_AUTHORITY_CONTRACT.md`. **Stage 2 in progress** (Slices 1–4 on path; Goals migrate 3b / workflows next).
4. **Phase 5 — Async EventBus** — implement `tiered_dispatch_policy.py` + `async_dispatch_queue.py` (currently only policy-only `dispatch_policy.py` exists); meet exit 5.4. *Gated by PERFORMANCE_CONSTITUTION Art. VII/XII — Performance Investigation Report + human approval before implementation.*
5. **Verification** — gates green on `main` per `PHASE_COMPLETION_RULE.md`.

> Queue 1 items 1a–1d landed on `main` (#105). Stage 2 State Authority is **unblocked**. Do not start Phase 5 Async EventBus without Performance Investigation Report + human approval. No Goose integration until Stage 3.

### Queue 2 — Evaluate (no implementation yet; Class B)

Goose / external patterns to assess **as reference only**: provider abstraction, plugin discovery, configuration, logging, desktop runtime. Each requires an Integration Proposal + ADR before any code.

### Queue 3 — Future (long-term backlog; Class C)

Pattern registry, plugin marketplace, advanced runtime, new UI ideas, performance.

---

## Immediate roadmap

1. **Stage 1 — Stabilization:** Phase B rem + truth matrix **done on `main` (#105)**. Remaining: R1 P2 wire-or-retire; EventBus only after approval. **No Goose integration.**
2. **Stage 2 — State Authority:** **in progress** — Slices 1–4 (query, planner, WM node+edge mutate, Goals quarantine + inventory); Goals migrate 3b / workflows next. No Goose unless it directly supports this work.
3. **Stage 3 — Goose Review:** only after the canonical roadmap reaches a stable checkpoint. Ask *"Which patterns strengthen the architecture we now have?"* — never *"How do we make ACC more like Goose?"*

---

## Change control (restated boundary)

These boundaries restate existing governance; they do not create new constitutional rules:

- Research **cannot** directly create implementation work.
- External repositories **cannot** directly change the roadmap.
- Every new architectural idea requires: (1) Integration Proposal, (2) Architecture approval (ADR if applicable), (3) Implementation plan, (4) Verification.

---

## Maintenance

This is a **living operational guide**, kept in sync with its authorities. The active implementation agent updates it when repository truth changes (new audit / merge to `main`), an ADR is accepted, the roadmap is re-sequenced by the owner, or a queue item lands. It never amends the Constitution, an ADR, or `PHASE_COMPLETION_RULE.md`; governance changes are made in those documents, and this guide follows.
