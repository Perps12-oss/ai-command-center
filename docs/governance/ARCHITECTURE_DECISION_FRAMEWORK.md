# Architecture Decision Framework

**Status:** ACTIVE — permanent decision-making process for major architecture changes  
**Authority:** Derives from `PROJECT_CONSTITUTION_V4.md` (Art. X–XII) and accepted ADRs.  
**Scope:** How ACC pressure-tests architecture before code. Does not amend the Constitution.  
**Related:** [`IMPLEMENTATION_GUIDE.md`](IMPLEMENTATION_GUIDE.md), [`docs/architecture/adr/README.md`](../architecture/adr/README.md), [`WORKSPACE_VISION.md`](../architecture/WORKSPACE_VISION.md)

---

## Philosophical shift

| Before | Now |
|--------|-----|
| “Is this a good implementation?” | “Is this the right architecture after surviving structured opposition?” |

Commodity agent patterns (LLM tool JSON, ReAct loops, CoT scratchpads, logprob autonomy) are **proposals**, not defaults. They must survive Architect defense, Red Team attack, Alternative first principles, Systems scoring, and Constitution Guardian identity review before any implementation plan is written.

---

## When this framework is mandatory

Use this process for:

- New planning, tool-invocation, memory, autonomy, or model-coupling architecture
- Any change that would make ACC more like a generic AI assistant / chatbot agent
- Superseding or narrowing an Accepted or Proposed ADR on live-path ownership
- Introducing a new EventBus authority or dual source of truth

Skip (use ordinary ADR / Integration Proposal) for:

- Localized bug fixes and refactors with no ownership change
- Docs-only clarifications that do not change binding rules
- Settings / UX polish within existing contracts

---

## Roles

| Role | Job | Must not |
|------|-----|----------|
| **Independent Review** | State the external or internal proposal exactly, without interpretation | Soften or “ACC-ify” the proposal |
| **Architect Council** | Best possible defense of the proposal | Concede Red Team points early |
| **Red Team** | Attempt to kill it — assumptions, scalability, uniqueness, maintainability, production behavior | Offer a mild tweak as “attack” |
| **Alternative Architecture** | Different first principle — not Proposal A v1.1 | Rebrand the same design |
| **Systems Review Board** | Score Proposal A vs B on the fixed criteria below | Decide Accept/Reject (that is Council) |
| **Constitution Guardian** | Identity only: Workspace OS, Inv 1–3/11/13, Program separation, debt, temporary-as-permanent | Overrule technical evidence; invent new constitutional text |
| **Council** | Accept / Reject / Hybrid with reasons | Skip Guardian or Systems scores |
| **Implementation** | Section 9 only after Council Decision — dependencies, milestones, tests, migration | Re-open architecture debate |

### Constitution Guardian checklist

1. Does this make ACC more like every other AI assistant?
2. Does it erode the Workspace OS vision (chat as one tool among many)?
3. Does it create architectural debt or dual authorities?
4. Does it weaken Program separation?
5. Is it introducing a temporary solution into permanent architecture?
6. Does it violate Invariants 1–3 (ownership / UI / EventBus), 11 (single SoT), or 13 (host supremacy)?

Guardian identifies **conflicts**. It does not invent technical winners. Council weighs Guardian findings against Systems scores.

---

## Standard ADR body (council format)

For decisions under this framework, ADRs use:

1. **Problem Statement**
2. **Current Repository** — evidence only; cite `IMPLEMENTATION_TRUTH_MATRIX.md` and code paths
3. **Independent Review Proposal** — verbatim intent of the proposal under review
4. **Architect Council** — best defense
5. **Red Team** — structured kill attempt
6. **Alternative Architecture Team** — different first principle
7. **Systems Review Board** — score table
8. **Constitution Guardian** — identity conflicts (input to decision)
9. **Council Decision** — Accept / Reject / Hybrid + reasons
10. **Actionable Implementation Plan** — only after decision; no architecture debate

Header fields remain: Status, Date, Deciders, Related, optional Baseline / Does not supersede.

### Systems scorecard (1–5)

| Criteria | Proposal A | Proposal B |
|----------|------------|------------|
| Simplicity | | |
| Performance | | |
| Reliability | | |
| Local LLM | | |
| Testability | | |
| Extensibility | | |
| Uniqueness (Workspace OS) | | |
| Production Risk | | |

Higher is better except **Production Risk** (1 = low risk, 5 = high risk). Guardian may force Hybrid even when A wins generic “agent” metrics.

---

## Authority wiring

```text
Research / external pattern / sprint roadmap
        │
        ▼
Integration Proposal (optional) ──► Council ADR (this framework)
        │
        ▼
Accepted / Rejected / Hybrid ADR
        │
        ▼
Section 9 Implementation Plan → code → verification
```

Per [`IMPLEMENTATION_GUIDE.md`](IMPLEMENTATION_GUIDE.md): research and external repos may inform; they may not override Constitution or Accepted ADRs. Implementation agents execute Section 9; they do not invent architecture.

Constitutional Pre-Flight (Art. X) remains mandatory before implementation. Review triggers (Art. XI) and AERs (Art. XII) still apply.

---

## Naming and location

- ADRs live in `docs/architecture/adr/`
- Filename: `ADR-NNN_UPPER_SNAKE_CASE.md`
- Next free number after existing series: see [`adr/README.md`](../architecture/adr/README.md)
- Do not reuse numbers (note historical ADR-007 collision)

Council-format ADRs from this process start at **ADR-018**.

---

## Identity anchors (Guardian reference)

- **Workspace OS** — ACC is not a chatbot with sidebar features ([`WORKSPACE_VISION.md`](../architecture/WORKSPACE_VISION.md))
- **Ownership** — UI → AppState → EventBus → Services → Repositories → Storage (Inv 1)
- **UI isolation** — UI renders and publishes intent only (Inv 2)
- **EventBus** — canonical runtime communication (Inv 3)
- **Single SoT** — one authoritative owner per domain (Inv 11)
- **Host supremacy** — externals are capabilities only (Inv 13, `AGENT_RUNTIME_INTERFACE.md`)

---

## Maintenance

This framework is living process documentation. Update it when Council practice reveals gaps. Binding architecture outcomes land in numbered ADRs, not here.
