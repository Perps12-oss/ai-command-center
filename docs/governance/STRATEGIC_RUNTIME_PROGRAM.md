# ACC Strategic Runtime & Architecture Completion Program

**Status:** ACTIVE — owner-authorized implementation program  
**Authority:** Derives from `PROJECT_CONSTITUTION_V4.md` and Accepted ADRs. This charter does **not** amend the Constitution.  
**Canonical queue:** [`IMPLEMENTATION_GUIDE.md`](IMPLEMENTATION_GUIDE.md) Queue 1 names this program.  
**Phase 0 baseline:** [`docs/audits/STRATEGIC_GAP_MATRIX.md`](../audits/STRATEGIC_GAP_MATRIX.md)  
**Pre-flight:** [`docs/audits/CONSTITUTIONAL_PRE_FLIGHT_STRATEGIC_RUNTIME_PROGRAM.md`](../audits/CONSTITUTIONAL_PRE_FLIGHT_STRATEGIC_RUNTIME_PROGRAM.md)

---

## Objective

Close accumulated architecture decisions and convert remaining strategic design into verified production capability — without letting items sit indefinitely as “gated.”

**“Gated” no longer means “parked indefinitely.”** It means **cannot advance past a defined decision checkpoint.**

Implementation agents do not own architecture. Repository governance defines authority and acceptance criteria. No particular LLM is the canonical implementer.

---

## Posture

| Stream | Work | Status after this charter |
|--------|------|---------------------------|
| A | ADR-021 Explainability | Implement **after** Gates 1–3 |
| B | ADR-022 Autonomy | Implement **after** Gates 1–3 |
| C | ADR-023 Model Strategy | Implement **after** Gates 1–3 |
| D | EventBus pool isolation / tiered dispatch | Implement **after** measurement + Gates 1–3 |
| E | Knowledge Federation | Implement **after** SoT ADR + Gates 1–3 |
| F | Goose pattern adoption | Implement **selectively** after Gates 1–3 |
| G | Cross-OS support | **ONLY remaining strategic gate** — last |
| X | macOS Hotkey (standalone) | **Dropped** |

Former “7 long-gated items” are replaced by **6 implementation streams + 1 final gate**. macOS hotkey is not a strategic architecture milestone; it may later appear only as an optional Cross-OS adapter feature.

---

## Pipeline (mandatory for every stream)

```text
Integration Proposal → ADR Decision → Section 9 Implementation Plan
        → Implementation → Verification → Close-out
```

| Gate | Name | Allowed work | Required outcome |
|------|------|--------------|------------------|
| 1 | Integration Proposal | Docs only | Answers the 10 questions below |
| 2 | ADR | Docs / council | **ACCEPT**, **REJECT**, or **DEFER WITH EXPLICIT CONDITION**. No indefinite pending. |
| 3 | Section 9 plan | Docs only | Files, interfaces, migrations, tests, wiring, docs, acceptance, rollback |
| 4 | Implementation | Code against Gate 3 only | No architecture invention in the PR |
| 5 | Verification | Tests + runtime + architecture + governance | Multi-level evidence |
| 6 | Close-out | Docs + evidence | Code + tests + docs + wiring + ADR + verification **agree** |

**No implementation starts against an unresolved architectural ambiguity.**

Existing Accepted ADRs (021–023) are **not** reopened by default. Gate 2 for those streams finalizes remaining Section 9 ambiguity (addendum or new ADR only if architecture must change). New numbers start at **ADR-024**.

### Gate 1 questions (every proposal)

1. What problem are we solving?  
2. What exists already?  
3. What architectural boundary owns it?  
4. What existing components must remain authoritative?  
5. What new behavior is required?  
6. What alternatives were rejected?  
7. What dependencies exist?  
8. What invariants must hold?  
9. How will it be tested?  
10. What would make the implementation invalid?

Gate 1 drafts: [`docs/architecture/proposals/`](../architecture/proposals/).

---

## Dependency order

```text
                    ┌───────────────────┐
                    │ Phase 0 Baseline  │
                    └─────────┬─────────┘
                              ↓
                  ┌──────────────────────┐
                  │ Architecture Gates  │
                  └──────────┬───────────┘
                             ↓
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
   Explainability       Autonomy             Model Strategy
        │                    │                    │
        └──────────────┬─────┴────────────┬───────┘
                       ↓                  ↓
                Runtime hardening    Provider layer
                       │                  │
                       └────────┬─────────┘
                                ↓
                         EventBus tuning
                                ↓
                       Knowledge Federation
                                ↓
                       Goose Pattern Review
                                ↓
                    Cross-OS Architecture Gate
```

Parallelism is allowed **inside a wave** only when dependencies remain explicit. Do not start Stream D isolation before measurement. Do not install a vector database before Stream E SoT ADR. Do not copy Goose into the runtime. Do not open Stream G before Waves 0–5 are closed on `main`.

---

## Waves

| Wave | Name | Queue 1 meaning |
|------|------|-----------------|
| 0 | Baseline | Strategic Gap Matrix (this establishment change) |
| 1 | Architecture closure | Finalize Gate 1–2 for A–F |
| 2 | Runtime foundations | Provider/model boundary; autonomy policy; explainability envelope; EventBus **measurement** (+ isolation only if justified) |
| 3 | Capability completion | Knowledge federation after SoT ADR; model M2–M4; autonomy escalation; explainability evidence surfaces |
| 4 | External pattern hardening | Goose Adopt/Adapt only; cleanup; regression |
| 5 | Full-system verification | Intent → routing → authorization → execution → verification → receipt → state projection → timeline → explanation |
| 6 | Cross-OS gate | Windows → Linux → macOS via **platform adapters**, not `if windows` in core |

Wave 0 and Gate 1 drafts may land together. **Stream code is Wave 2+ and is not authorized until Gates 2–3.**

---

## Effort envelope

Initial program envelope: **97–167 hours** (planning range, not a commitment). Cross-OS is **outside** that envelope as a separate major program (Stream G).

| Workstream | Relative effort |
|------------|-----------------|
| Baseline / architecture decisions | Small |
| Explainability | Small–Medium |
| Autonomy | Medium |
| Model Strategy | Medium |
| EventBus | Medium |
| Knowledge Federation | Medium–Large |
| Goose adoption | Small |
| Cross-OS | Separate major program |

---

## Definition: strategic backlog cleared

The six streams are **not** cleared because a feature demo works. Cleared only when **all** of:

- Every stream has an accepted ADR (or explicit REJECT / DEFER WITH CONDITION).
- Every accepted ADR has a Section 9 plan.
- Every implementation is wired into the canonical runtime.
- No parallel/legacy execution path bypasses ExecutionAuthority / receipts / TruthBoundary / state projection.
- Runtime receipts/evidence prove the new behaviour.
- Unit / integration / runtime tests pass.
- Architecture documentation matches implementation.
- Governance documentation matches the actual workflow.
- No unresolved “temporary” architecture remains without an explicit owner and condition.
- The six formerly gated items are formally closed.
- **Cross-OS is the only remaining strategic gate.**

`PHASE_COMPLETION_RULE.md` still applies: nothing is complete until it is on `main`.

---

## Stream rules (non-negotiable)

### A — Explainability

Decision → rationale → evidence → policy/context → outcome.  
Records derive from **runtime state**, not generated retrospective prose. The LLM may compose wording; it is not SoT for what happened.

### B — Autonomy

observe → classify → decide → authorize/escalate → execute → verify.  
Autonomy decides **how much authority is permitted**. It is not a second execution pathway. Exact thresholds come from Gate 2, not from implementers.

### C — Model Strategy

task → capability requirements → model selection → execution → verification → fallback.  
**The model does not own routing authority.** Runtime chooses the model. M2–M4 sequential.

### D — EventBus

Measurement first (queue depth, dispatch latency, handler duration, contention, burst, UI impact, starvation, cross-topic interference). Smallest justified isolation. `PERFORMANCE_CONSTITUTION.md` is verification authority. Abandoned pool branch is **not** a merge candidate.

### E — Knowledge Federation

Do **not** begin by installing a vector database. Authoritative State → Knowledge Projection → Retrieval Index → Semantic Search → Context Assembly. Vector index is **derived**, never SoT. UCGS `scope_embeddings` remains S5 until Gate 2 + profile enablement.

### F — Goose

Not Goose compatibility. Adopt / Adapt / Reject only. Deliverable: Goose Pattern Adoption Record.

### G — Cross-OS

ACC core stays platform-independent. Windows / macOS / Linux adapters behind a platform interface. Hotkeys, tray, packaging are adapter features — not the program’s identity.

### X — Dropped

Standalone macOS Hotkey strategic item is removed. Incomplete `platform/macos` tap stubs are fossils, not Queue 1.

---

## What this program does not authorize

- Restoring retired packages (ADR-006 / 012 / 013 / 014) without a **superseding** ADR.
- Implementing from `docs/plans/` historical phase files.
- Weakening CI, UCGS, or arch-lint to go green.
- Declaring phases complete off `main`.
