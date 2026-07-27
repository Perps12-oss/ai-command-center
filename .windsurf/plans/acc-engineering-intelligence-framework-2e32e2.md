# ACC Engineering Intelligence Framework

Establish a top-level `research/` workspace with standardized templates, scoring rubrics, and a promotion-to-ADR workflow so every open-source repository studied by ACC produces comparable, reusable engineering intelligence.

## Scope

Phase 1 only: scaffold the framework. No repository-specific content. Goose will be the first pilot expedition in Phase 2, but the framework must exist first so Goose populates it rather than inventing its own structure.

## Deliverables

### 1. Top-level workspace

Create `research/` at the repository root:

```text
research/
├── README.md
├── CONSTITUTION.md
├── index.md
├── repositories/
│   ├── index.md
│   └── {expedition-id}-{repo-name}/
│       ├── report.md
│       ├── patterns.md
│       ├── decisions.md
│       └── notes/
├── patterns/
│   ├── index.md
│   └── PAT-NNN.md
├── decisions/
│   ├── index.md
│   └── RD-NNN.md
├── comparisons/
├── integration/
├── templates/
│   ├── repository/
│   ├── pattern/
│   │   ├── pattern_candidate_template.md
│   │   ├── pattern_validation_template.md
│   │   └── pattern_registry_entry_template.md
│   ├── comparison/
│   └── integration/
├── prompts/
├── scoring/
└── backlog/
```

### 2. Core documents

- `research/README.md` — purpose, lifecycle, how to start an expedition, how to promote a pattern to ADR, and how the framework relates to `docs/` and `governance/`.
- `research/CONSTITUTION.md` — governing rules for all research work.
- `research/index.md` — master catalog linking repositories, patterns, decisions, comparisons, integration proposals, and resulting ADRs.
- `research/repositories/index.md` — repository registry with ID, repository, status, and expedition folder link. Scales as each repository gets its own folder under `repositories/`.
- `research/patterns/index.md` — Pattern Registry with ID, pattern name, source repository, and status (`Candidate`, `Validated`, `Approved`, `Rejected`).
- `research/decisions/index.md` — research decision log (RD-xxx) recording investigation outcomes without elevating them to architecture decisions.

### 3. Templates

Located under `research/templates/`, each with a frontmatter schema and fillable sections:

- `repository/repository_template.md` — expedition report covering architecture, runtime, state, providers, plugins, UI, execution, security, testing, performance, pattern candidates, risks, and integration opportunities.
- `pattern/pattern_candidate_template.md` — raw engineering idea extracted from a repository before validation.
- `pattern/pattern_validation_template.md` — evaluation of whether a candidate should become an official, reusable ACC pattern.
- `pattern/pattern_registry_entry_template.md` — final pattern card for the Pattern Registry.
- `comparison/comparison_template.md` — side-by-side matrix of multiple repositories against a set of patterns or subsystems.
- `integration/integration_proposal_template.md` — proposal with title, rationale, files affected, estimated effort, risk, dependencies, and recommendation status.
- `decision/research_decision_template.md` — record of an investigation outcome (`Proceed`, `Reject`, `Hold`) with rationale and reuse reference.

### 4. Scoring framework

`research/scoring/framework.md` defines dimensions and rubrics:

- Engineering quality
- Architectural complexity
- Reuse potential
- ACC architecture fit
- Integration risk

Each produces a score and a recommendation: `Immediate`, `Adapt`, `Future`, `Reject`.

### 5. Pattern Registry

`research/patterns/index.md` is the canonical registry of reusable engineering ideas. Each entry has:

| Field | Purpose |
|-------|---------|
| ID | `PAT-NNN` |
| Pattern | Short name |
| Source Repository | Where it was extracted |
| Status | `Candidate` → `Validated` → `Approved` / `Rejected` |
| Related RD | Research decision that validated or rejected it |
| ADR | Link to architecture decision record, if adopted |

Per-pattern files (`PAT-NNN.md`) are created only after validation. Candidates live in `templates/pattern/pattern_candidate_template.md` instances inside the repository folder until promoted.

### 6. Research Decisions

`research/decisions/index.md` logs investigation outcomes as `RD-NNN` records. These are research conclusions, not architecture decisions. They prevent re-investigating the same repository later.

Example decisions:

- `RD-001` — Goose investigated. Result: Proceed with integration proposals.
- `RD-002` — LangGraph investigated. Result: Rejected. Reason: Conversation-centric architecture conflicts with ACC Workspace OS authority model.

### 7. Expedition checklist

`research/templates/expedition_checklist.md` standardizes the repository investigation process:

1. Register repository in `research/repositories/index.md` and create `repositories/{expedition-id}-{repo-name}/`.
2. Clone or locate source.
3. Fill `repository/repository_template.md`.
4. Extract pattern candidates and store them in the repository folder.
5. Validate each candidate against ACC architecture using `pattern/pattern_validation_template.md`.
6. Promote validated patterns to the Pattern Registry (`patterns/index.md` and `PAT-NNN.md`).
7. Record research decisions in `decisions/index.md` (`RD-NNN.md`).
8. Produce compatibility review and comparison matrices.
9. Draft integration proposals where appropriate.
10. Submit for Architecture Review (Tom).
11. Update `research/index.md` with RD, pattern, and ADR or rejection links.

### 8. Research Constitution

`research/CONSTITUTION.md` establishes discipline:

1. **Research is descriptive, never prescriptive.**
2. **No code may be copied without understanding the underlying pattern.**
3. **Every adopted pattern must trace back to a Pattern Registry entry, an Integration Proposal, and an ADR.**
4. **Every investigated repository must produce a Research Decision (RD).**
5. **ACC architecture always takes precedence over external projects.**
6. **The goal is to extract engineering patterns, not replicate products.**

### 9. Pattern lifecycle and promotion pipeline

Documented in `research/README.md` and `research/CONSTITUTION.md`:

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

Research may recommend. Research cannot decide. Only validated patterns are added to the Pattern Registry, and only registry entries that pass Architecture Review receive an ADR and implementation work.

### 10. Backlog

`research/backlog/repositories.md` lists candidate repositories with subsystems, priority, and assigned expedition ID. Initial seed entries include Goose, OpenHands, LibreChat, PyGPT, Logseq, Obsidian, React Flow, Yjs, and VS Code.

## Sequencing

| Phase | Work | Output |
|-------|------|--------|
| 1 | Foundation | This `research/` scaffold with Pattern Registry, Research Decisions, and repository index |
| 2 | Goose Pilot | First populated expedition report, pattern candidates, validations, and research decisions |
| 3 | Inspiration Index | Indexed repository library, Pattern Registry, and comparison matrix |

## Verification

- All directories and files in the structure above exist.
- `research/repositories/index.md`, `research/patterns/index.md`, and `research/decisions/index.md` exist and are referenced from `research/index.md`.
- Templates contain frontmatter and are fillable.
- `index.md` references every scaffolded artifact.
- `CONSTITUTION.md` and `README.md` state the Pattern Lifecycle, promotion pipeline, and the boundary between research and authoritative architecture.
- No files are created under `docs/`, `governance/`, `ai_command_center/`, or any runtime code path.

## Governance note

Research artifacts are descriptive and non-authoritative. They do not modify the Constitution, architecture, contracts, or runtime code. Only patterns promoted through Architecture Review and recorded in `docs/architecture/adr/` may influence implementation. This Phase 1 task is therefore a documentation/research infrastructure change only.

