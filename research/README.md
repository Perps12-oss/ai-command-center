# ACC Engineering Intelligence Program

This workspace governs how AI Command Center studies, catalogs, and learns from external open-source repositories.

It is a research laboratory, not an authority. Nothing in this directory is architecture. Approved ideas graduate to `docs/architecture/adr/` before implementation.

## Purpose

- Discover engineering patterns in mature open-source projects.
- Evaluate their fit for ACC without changing ACC's authority model.
- Maintain reusable pattern cards and research decisions.
- Feed integration proposals into the Architecture Review process.

## Lifecycle

```text
Repository Expedition
       ↓
Pattern Candidate extraction
       ↓
Pattern Validation (ACC fit, reuse, risk)
       ↓
Pattern Registry (PAT-NNN)
       ↓
Integration Proposal
       ↓
Architecture Review (Tom)
       ↓
ADR in docs/architecture/adr/
       ↓
Implementation Plan
       ↓
Implementation
       ↓
Verification
       ↓
Documentation
```

Research may recommend. Research cannot decide.

## Directory map

| Directory | Purpose |
|-----------|---------|
| `repositories/` | One folder per investigated repository. Contains report, extracted candidates, and research decision. |
| `patterns/` | Pattern Registry (`index.md`) and validated pattern cards (`PAT-NNN.md`). |
| `decisions/` | Research decision log (`RD-NNN.md`). |
| `comparisons/` | Side-by-side comparisons across repositories or patterns. |
| `integration/` | Integration proposals ready for Architecture Review. |
| `templates/` | Fillable templates for expeditions, patterns, comparisons, proposals, and decisions. |
| `prompts/` | Reusable prompts for repository audits and pattern extraction. |
| `scoring/` | Scoring rubric and framework for evaluations. |
| `backlog/` | Queue of candidate repositories to study. |

## Quickstart

1. Pick a repository from `backlog/repositories.md` (IDs are already reserved in `repositories/index.md` as `exp-NNN`).
2. Create `repositories/{exp-NNN}-{repo-name}/` using the reserved ID (do not invent a parallel ID scheme).
3. Copy `templates/repository/repository_template.md` into the folder as `report.md`.
4. Extract pattern candidates and validate them.
5. Promote validated patterns to `patterns/index.md`.
6. Record the research decision in `decisions/index.md`.
7. If appropriate, draft an integration proposal in `integration/`.

## Relation to governance

- `research/` = descriptive intelligence (not architecture authority)
- `docs/architecture/adr/` = Accepted ADRs bind under V4; Proposed are non-binding
- `governance/` = constitutional **recordkeeping** (ledger, templates, AER forms) — **not** the supreme constitution (`PROJECT_CONSTITUTION_V4.md` is)

A pattern may only influence implementation after it has an Integration Proposal, passes Architecture Review, and is recorded as an **Accepted** ADR.
