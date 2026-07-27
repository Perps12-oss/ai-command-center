# Implementation Guide

**Status:** ACTIVE — subordinate operational guide (living document)
**Authority:** **Derives its authority entirely from `PROJECT_CONSTITUTION_V4.md` and the accepted ADRs** (e.g. `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`). This guide is **not** an independent authority.
**Scope:** Operationalizes *how* implementation is carried out. It **introduces no new governing rules**; it only restates and applies rules already established by the Constitution, the ADRs, and existing governance (`docs/governance/PHASE_COMPLETION_RULE.md`).
**Related:** `docs/plans/README.md`, `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md`, `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`

> **Precedence of this document:** If anything here ever conflicts with `PROJECT_CONSTITUTION_V4.md`, an ADR, or `PHASE_COMPLETION_RULE.md`, those sources win and this guide is corrected. Changes to the underlying governance are made in those documents, not here.

---

## Purpose

ACC's development has moved from **multiple agents making overlapping implementation decisions** to **one implementation role consuming evidence from multiple sources**. This mirrors ACC's own architecture: **separate discovery from execution**.

This guide describes how that single implementation role (Devin) executes work under existing governance. There is one place where implementation is *carried out*; **decisions about architecture, governance, and roadmap remain owned by the Constitution, the ADRs, and the project owner.**

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
 Repository Truth ───────────► Devin ◄─────────── Architecture
     (Tom Audit)                                  (ADR / Constitution)
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

Devin acts as the **implementation role** — an executor, not an authority. Everything else is an evidence source.

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

Those arrive as **inputs** from their owning authorities. Devin may surface them as proposals; it may not enact them unilaterally.

---

## Authority order (restated, not created)

The order below **restates** the precedence already established by `PROJECT_CONSTITUTION_V4.md` and the ADRs so implementers have it in one place. It creates no new hierarchy.

| # | Source | Examples |
|---|--------|----------|
| 1 | **`PROJECT_CONSTITUTION_V4.md`** — supreme authority | plus peer constitutions `PERFORMANCE_CONSTITUTION.md`, `docs/UI_CONSTITUTION.md` |
| 2 | **ADRs** | `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`, etc. |
| 3 | **Repository truth** — current implementation + verified audits on `origin/main` | `IMPLEMENTATION_TRUTH_MATRIX.md`, Tom audits, code on `main` |
| 4 | **Canonical roadmap** | `docs/MASTER_ROADMAP_2026.md`, `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md` |
| 5 | **Approved implementation plans** | `docs/plans/PHASE_*.md` (active, code-verified) |
| 6 | **Research (Engineering Intelligence)** | expedition / pattern reports |
| 7 | **External repositories** | Goose, OpenHands, CrewAI, etc. |

> **Applying the existing rule:** consistent with the Constitution and `PHASE_COMPLETION_RULE.md`, lower-precedence sources may *inform* higher-precedence ones but may not *override* them. Research (6) may motivate a roadmap change (4) only via an accepted ADR (2) / owner decision; an external repo (7) may never silently change ACC's direction. This is a restatement of existing governance, not a new rule.
>
> Note: `PHASE_COMPLETION_RULE.md` ("main is the only truth") governs *when a phase may be called complete*; for that judgement, audited code on `origin/main` is authoritative. It does not subordinate the Constitution or ADRs, which remain supreme for *decisions*.

---

## Decision process (before touching any code)

An operational checklist for applying the authority order above:

```text
Does repository truth / an approved plan already require this?
   └─ YES → Implement.
   └─ NO ↓

Does the Constitution or an ADR approve it?
   └─ YES → Implement.
   └─ NO ↓

Does research (6) recommend it?
   └─ YES → Create an Integration Proposal (for ADR / owner review). Do NOT implement.
   └─ NO ↓

Ignore.
```

This prevents **research creep** and **external-project creep**.

---

## Evidence classes

Incoming information is triaged into three classes:

- **Class A — Repository Truth (Authoritative):** comes from the repo; Devin trusts it. (e.g. Phase B has four outstanding conditions; Phase 5 Async EventBus incomplete; Operator Kernel intentionally unwired; State Authority is the next architectural milestone.)
- **Class B — Engineering Intelligence (Reference):** e.g. Goose provider abstraction / extension system / runtime / desktop architecture. Reference material, **not** implementation instructions.
- **Class C — Future Opportunities (Backlog):** e.g. potential provider registry, plugin registry, runtime improvements. Backlog, **not** current work.

---

## The three queues

### Queue 1 — Must Do (blocks progress; from repository truth + approved plans)

Source: EPOCH A audit + `PHASE_R1_RUNTIME_RECONCILIATION.md`. Ordered:

1. **Phase B remediation (close program conditions):**
   - Fix E07 Goal Workspace inspect kind — publish/register `"task"` instead of unregistered `"plan_step"` (`ai_command_center/ui/views/goal_view.py:319`, `ai_command_center/ui/shell/view_manager.py:568`). **High.**
   - Add active-goal projection to E02 `GlobalContextBar` (`ai_command_center/ui/components/global_context_bar.py`).
   - Backfill Tom audit artifacts for E00–E03 on `main`.
   - Refresh `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md` for Phase B UI surfaces.
2. **PHASE R1 — Runtime Reconciliation** (priority order: Runtime authority → Composition → State → UI → Features; no Priority N+1 before N's gate passes).
3. **State Authority Contract** (R1 Priority 3) — `docs/architecture/STATE_AUTHORITY_CONTRACT.md`.
4. **Phase 5 — Async EventBus** — implement `tiered_dispatch_policy.py` + `async_dispatch_queue.py` (currently only policy-only `dispatch_policy.py` exists); meet exit 5.4. *Gated by PERFORMANCE_CONSTITUTION Art. VII/XII — Performance Investigation Report + human approval before implementation.*
5. **Verification** — gates green on `main` per `PHASE_COMPLETION_RULE.md`.

> Per the Tom Phase-B package audit, do not declare Phase B COMPLETE or start Phase 12 / State Authority feature work until Queue 1 items 1a–1d land.

### Queue 2 — Evaluate (no implementation yet; Class B)

Goose / external patterns to assess **as reference only**: provider abstraction, plugin discovery, configuration, logging, desktop runtime. Each requires an Integration Proposal + ADR before any code.

### Queue 3 — Future (long-term backlog; Class C)

Pattern registry, plugin marketplace, advanced runtime, new UI ideas, performance.

---

## Immediate roadmap

1. **Stage 1 — Stabilization:** complete everything Tom identified (Phase B remediation, Runtime Reconciliation, EventBus, Truth Matrix, Verification). **No Goose integration.**
2. **Stage 2 — State Authority:** implement the canonical architecture. No Goose integration unless it directly supports this work.
3. **Stage 3 — Goose Review:** only after the canonical roadmap reaches a stable checkpoint. Ask *"Which patterns strengthen the architecture we now have?"* — never *"How do we make ACC more like Goose?"*

---

## Maintenance

This is a **living operational guide**, kept in sync with its authorities. Devin updates it when repository truth changes (new audit / merge to `main`), an ADR is accepted, the roadmap is re-sequenced by the owner, or a queue item lands. It never amends the Constitution, an ADR, or `PHASE_COMPLETION_RULE.md`; governance changes are made in those documents, and this guide follows.
