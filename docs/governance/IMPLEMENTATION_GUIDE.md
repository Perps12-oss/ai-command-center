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

- **Class A — Repository Truth (Authoritative):** comes from the repo; the implementation agent trusts it. (e.g. Phase B CONDITIONS cleared on `main` (#105); Stage 2 soft-shadow + R1 P1–P4 + ADR-014–017 on `main`; SA.mutate track **CLOSED**; Phase 5 Async EventBus incomplete and **approval-gated**; OperatorKernel / Predictive / Undo **retired from live**.)
- **Class B — Engineering Intelligence (Reference):** e.g. Goose provider abstraction / extension system / runtime / desktop architecture. Reference material, **not** implementation instructions.
- **Class C — Future Opportunities (Backlog):** e.g. potential provider registry, plugin registry, runtime improvements. Backlog, **not** current work.

---

## The three queues

### Queue 1 — Must Do (blocks progress; from repository truth + approved plans)

Source: EPOCH A audit + `PHASE_R1_RUNTIME_RECONCILIATION.md`. Ordered:

1. **Phase B remediation (close program conditions):** ✅ **on `main`** via [#105](https://github.com/Perps12-oss/ai-command-center/pull/105) (`f03a4fa`, 2026-07-29). Phase B UI program CONDITIONS cleared.
2. **PHASE R1 — Runtime Reconciliation** — P1–P4 **passed**; P5 Predictive/Undo **disposition closed (ADR-014 research-only)**. Composition retire rows: ADR-006/012/013/014. Soft-shadow Stage 2 **closed**.
3. **State Authority Contract** — soft-shadow complete; live mutate = WM + Memory + Goals; workflows/executions/agents **remain outside (ADR-017)** — R1 SA.mutate track **CLOSED**.
4. **Phase 5 — Async EventBus** — implement `tiered_dispatch_policy.py` + `async_dispatch_queue.py` (currently only policy-only `dispatch_policy.py` exists); meet exit 5.4. *Gated by PERFORMANCE_CONSTITUTION Art. VII/XII — Performance Investigation Report + human approval before implementation.*
5. **Verification** — gates green on `main` per `PHASE_COMPLETION_RULE.md`.

> Ungated Stage 2 / R1 P1–P5 disposition work is on `main`. See `docs/audits/R1_UNGATED_STOP_LINE.md`. Do not start Phase 5 Async EventBus without Performance Investigation Report + human approval. No Goose until Stage 3.

### Queue 2 — Evaluate (no implementation yet; Class B)

Goose / external patterns to assess **as reference only**: provider abstraction, plugin discovery, configuration, logging, desktop runtime. Each requires an Integration Proposal + ADR before any code.

### Queue 3 — Future (long-term backlog; Class C)

Pattern registry, plugin marketplace, advanced runtime, new UI ideas, performance. Platform hotkey/tray live wire = Phase 11 backlog (not R1 blocker).

---

## Immediate roadmap

1. **Stage 1 — Stabilization:** Phase B rem + truth matrix **done on `main` (#105)**. R1 P2 wire-or-retire **closed** (ADR-006/012/013/014). EventBus only after approval. **No Goose integration.**
2. **Stage 2 — State Authority / R1 closeout:** **soft-shadow closed**; **P4/P5 closed**; **ADR-015/016 mutate live**; **ADR-017 WEA disposition** — **SA.mutate track CLOSED** (`R1_UNGATED_STOP_LINE.md`). Parallel other tracks: Goose = Stage 3; Async EventBus = Phase 5 + approval; live-wire Predictive/Undo only with ADR superseding 014.
3. **Stage 3 — Goose Review:** only after the canonical roadmap reaches a stable checkpoint. Ask *"Which patterns strengthen the architecture we now have?"* — never *"How do we make ACC more like Goose?"*

---

## Change control (restated boundary)

These boundaries restate existing governance; they do not create new constitutional rules:

- Research **cannot** directly create implementation work.
- External repositories **cannot** directly change the roadmap.
- Every new architectural idea requires: (1) Integration Proposal, (2) Architecture approval (ADR if applicable — **multi-council framework** when major), (3) Implementation plan (ADR Section 9 after Council Decision), (4) Verification.

---

## Maintenance

This is a **living operational guide**, kept in sync with its authorities. The active implementation agent updates it when repository truth changes (new audit / merge to `main`), an ADR is accepted, the roadmap is re-sequenced by the owner, or a queue item lands. It never amends the Constitution, an ADR, or `PHASE_COMPLETION_RULE.md`; governance changes are made in those documents, and this guide follows.
