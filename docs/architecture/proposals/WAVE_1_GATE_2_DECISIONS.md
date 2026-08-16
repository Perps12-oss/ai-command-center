# Wave 1 — Gate 2 Decisions (Architecture Closure)

**Status:** CLOSED 2026-08-14 — owner Gate 2 decisions recorded for Streams A–F
**Program:** [`STRATEGIC_RUNTIME_PROGRAM.md`](../../governance/STRATEGIC_RUNTIME_PROGRAM.md)
**Baseline:** [`STRATEGIC_GAP_MATRIX.md`](../../audits/STRATEGIC_GAP_MATRIX.md) (Phase 0)
**Rule applied:** Gate 2 = **ACCEPT**, **REJECT**, or **DEFER WITH EXPLICIT CONDITION**. No indefinite pending — every stream below resolves to one of those three, with a named next step.

This document is the single place to check "is Wave 1 done." It does not restate the reasoning in each ADR/proposal — follow the links for that. Per `PHASE_COMPLETION_RULE.md`, Wave 1 is not complete until this file (and the ADR/proposal edits it references) are on `main`.

---

## Decisions

| Stream | Gate 2 ask | Decision | Recorded in | Wave 2+ authorization |
|---|---|---|---|---|
| **A** — Explainability | ACCEPT full M2–M5 or DEFER named milestones | **ACCEPT** — full M2–M5, no deferral | [`ADR-021` §11](../adr/ADR-021_EXPLAINABILITY.md#11-gate-2-addendum--wave-1-closure-2026-08-14) | Gate 3 Section 9 plan authorized next |
| **B** — Autonomy | ACCEPT numeric bands + block-vs-escalate | **ACCEPT** — escalate-only, bands `<0.4` HIGH / `0.4<=score<0.7` MEDIUM / `>=0.7` LOW; low score never independently blocks | [`ADR-022` §11](../adr/ADR-022_CONFIDENCE_AND_AUTONOMY.md#11-gate-2-addendum--wave-1-closure-2026-08-14) | Gate 3 Section 9 plan authorized next |
| **C** — Model Strategy | ACCEPT sequential M2→M4 or DEFER milestones | **ACCEPT** — full M2→M3→M4, sequential; capability-registry extras explicitly out of scope (future proposal) | [`ADR-023` §11](../adr/ADR-023_MODEL_STRATEGY.md#11-gate-2-addendum--wave-1-closure-2026-08-14) | Gate 3 Section 9 plan authorized next (M2 first) |
| **D** — EventBus isolation | ACCEPT / REJECT / DEFER WITH CONDITION | **DEFER WITH CONDITION** — Stage 1 Performance Investigation Report required before any isolation decision; no ADR issued yet | [`IP_D_EVENTBUS_ISOLATION.md` §11](IP_D_EVENTBUS_ISOLATION.md#11-gate-2-decision--wave-1-closure-2026-08-14) | Stage 1 instrumentation/load-testing only. Stage 2 (isolation) stays blocked until the report exists and Gate 2 reopens. |
| **E** — Knowledge Federation | New ADR-024: ACCEPT derived-index / REJECT vectors / DEFER WITH CONDITION | **DEFER WITH CONDITION** — live-wire read-only `FederationService` now; no embeddings/vector index; UCGS `scope_embeddings` stays S5 | [`ADR-024`](../adr/ADR-024_KNOWLEDGE_FEDERATION_SOT.md) | Gate 3 plan authorized for the read-only wiring only. Vector/semantic search remains gated behind a future proposal. |
| **F** — Goose pattern adoption | ACCEPT Adopt/Adapt/Reject table or REJECT track | **ACCEPT** — table as drafted in IP-F, unedited | [`ADR-025`](../adr/ADR-025_GOOSE_PATTERN_ADOPTION.md) / [`GOOSE_PATTERN_ADOPTION_RECORD.md`](GOOSE_PATTERN_ADOPTION_RECORD.md) | Adapt rows scheduled for Wave 4 (after A–C runtime contracts are stable), each behind its own Gate 3 plan. Not implemented now. |

**Stream G (Cross-OS)** is unaffected by this closure — it remains the final strategic gate, not opened until Waves 0–5 close on `main`, per program charter.

---

## ADR numbering assigned by this closure

- **ADR-024** → Stream E (Knowledge Federation SoT)
- **ADR-025** → Stream F (Goose Pattern Adoption)
- **Next free number: ADR-026** (informally reserved for Stream D's isolation ADR if/when a Stage 1 report justifies one — see ADR README before drafting, in case other work claims it first)

See [`docs/architecture/adr/README.md`](../adr/README.md) for the updated index.

---

## What this closure does and does not authorize

**Authorized now (Gate 3 — Section 9 implementation plans; still docs, no code):**
- Streams A, B, C: full remaining Section 9 scope as decided above.
- Stream E: the read-only federation wiring only.
- Stream D: Stage 1 instrumentation and load-test design (measurement is not an architecture decision).

**Still blocked:**
- Any actual product code for Streams A–F (Gate 4 is code; it requires a Gate 3 plan first, not just this Gate 2 decision — per the pipeline in `STRATEGIC_RUNTIME_PROGRAM.md`).
- Stream D isolation topology (needs the Stage 1 report + a fresh Gate 2 review of that report).
- Stream E embeddings/vector search (needs its own future proposal + UCGS profile change).
- Stream F Adapt-row implementation (scheduled Wave 4, not now).
- Stream G (Cross-OS) — untouched, opens only after Waves 0–5.

**No implementation agent — human or AI — should start Gate 4 code against any of the above without first producing the Gate 3 Section 9 plan named in the relevant ADR/proposal.**

---

## Definition-of-done check (Wave 1)

Per `STRATEGIC_RUNTIME_PROGRAM.md` "Definition: strategic backlog cleared," Wave 1 specifically requires *"Every stream has an accepted ADR (or explicit REJECT / DEFER WITH CONDITION)."* Status:

- [x] A — Accepted (ADR-021 §11)
- [x] B — Accepted (ADR-022 §11)
- [x] C — Accepted (ADR-023 §11)
- [x] D — DEFER WITH CONDITION (IP-D §11; no ADR — none required for a defer)
- [x] E — DEFER WITH CONDITION (ADR-024)
- [x] F — Accepted (ADR-025)

**Wave 1 (Architecture closure, Gate 1–2) is closed for all six streams once this file and the linked edits land on `main`.** Wave 2 (Runtime foundations) is authorized to begin Gate 3 planning for Streams A, B, C, and E's read-only slice. Stream D remains at Stage 1 measurement. Stream F remains parked until Wave 4.

---

## References

- `docs/governance/STRATEGIC_RUNTIME_PROGRAM.md`
- `docs/governance/IMPLEMENTATION_GUIDE.md` (Queue 1)
- `docs/audits/STRATEGIC_GAP_MATRIX.md`
- `docs/architecture/adr/README.md`
- `docs/architecture/proposals/IP_A_EXPLAINABILITY.md` … `IP_F_GOOSE_PATTERN_ADOPTION.md`
