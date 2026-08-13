---
name: adr-review
description: >-
  Run ACC's Architecture Decision Review process — a 7-role adversarial
  framework (Independent Reviewer, Architect Council, Red Team, Alternative
  Architecture Team, Systems Review Board, Council Decision, Constitution
  Guardian) that pressure-tests a major architecture decision before any code
  is written. Use when asked to review an architecture decision, run an ADR
  review, evaluate a proposed architecture change, challenge an architecture
  proposal, or run /adr-review.
---

# ACC Architecture Decision Review — permanent framework

Use this skill when asked to run `/adr-review` or evaluate a major architecture decision.

**The question this process answers is never "is this a good implementation."** It's: *is this the right architecture after surviving structured opposition?* If you catch yourself writing an implementation-quality assessment instead of running the adversarial process below, stop and restart.

**Authority config:** `docs/agents/adr-review-config.json` (ADR seed definitions, scoring criteria weights, independence map — load and follow it).

**Output template:** `docs/architecture/adr/TEMPLATE_ADR_REVIEW.md` (mandatory 9-section structure — every review fills the same sections in the same order, no skipping, no reordering).

**This is the canonical skill definition.** A copy also lives at `.cursor/skills/adr-review/SKILL.md`, kept identical to this file — the same lesson learned the hard way with the `tom-auditor` skill (see its own file history). Edit one, copy the change to the other in the same commit.

## When to use

- User asks to review, decide, or re-open a major architecture question (tool invocation, planning model, memory model, explainability, autonomy/confidence, model dependency, or similar structural decisions)
- Before committing to an architecture direction that would be expensive to reverse once code is written
- When two credible architectures are both plausible and the choice has long-term identity consequences for ACC, not just implementation cost

**Not for:** routine implementation review of code already written against an already-decided architecture — that's Tom's job (`tom-auditor` skill), not this one.

## The seven roles

1. **Independent Reviewer** (orchestrator — you, before any adversarial role runs) — read `Current Repository` evidence only and state exactly what you'd recommend. No interpretation, no hedging, no "it depends." This becomes the proposal the Architect Council defends.
2. **Architect Council** (orchestrator) — the best possible defense of the Independent Reviewer's proposal, grounded in the evidence gathered, not enthusiasm.
3. **Red Team** (independent subagent — see Independence Map) — attempts to kill the proposal. Must attack five things specifically: assumptions, scalability, uniqueness, maintainability, and production behavior. Generic skepticism doesn't satisfy this role.
4. **Alternative Architecture Team** (independent subagent) — proposes a genuinely different first-principles architecture. Not a v1.1 tweak of the reviewed proposal. If what comes out is a variant with the same bones, that's a failed run of this role — redo it.
5. **Constitution Guardian** (independent subagent) — the one role that isn't adversarial to the proposal, it's adversarial to drift. Answers exactly one question: *does this violate the Constitution or the long-term identity of ACC* — does it make ACC more like every other AI assistant, erode the Workspace OS vision, create architectural debt, weaken Program separation, or smuggle a temporary solution into permanent architecture? This role does not evaluate technical merit and must not try to. It also cannot be overruled by technical merit — see Council Decision.
6. **Systems Review Board** (orchestrator) — scores the original proposal and the alternative against the 8 criteria in the config, using Architect Council + Red Team + Alternative Team + Constitution Guardian output as its evidence base, not fresh opinion.
7. **Council Decision** (orchestrator) — Accept / Reject / Hybrid, with explicit reasons, and an explicit statement of how the Constitution Guardian's finding was weighed — even when the finding is "no conflict found." Constitution Guardian can veto on identity grounds even if the Systems Board scores favor the proposal; the Systems Board cannot overrule a Guardian veto by scoring around it. If the two conflict, Council Decision must say so explicitly and explain the resolution rather than silently picking one.

## Independence Map — who may see what

| Role | Sees | Must NOT see |
|---|---|---|
| Architect Council | Independent Reviewer's proposal, Current Repository evidence | N/A (nothing else exists yet at this point) |
| Red Team | Problem Statement, Current Repository evidence, Independent Reviewer's proposal | Architect Council's defense — attack the proposal itself, not the rhetoric defending it |
| Alternative Architecture Team | Problem Statement, Current Repository evidence **only** | The proposal, Architect Council's defense, Red Team's attack — must not anchor on what it's "supposed" to differ from |
| Constitution Guardian | Problem Statement, Current Repository evidence, the proposal, and the alternative | Systems Board scores, Council Decision — must not know which way the process is leaning |
| Systems Review Board | Everything produced so far | — (synthesis role) |
| Council Decision | Everything, including Systems Board scores | — (final synthesis role) |

**Red Team, Alternative Architecture Team, and Constitution Guardian must be launched via the Agent tool as separate subagent invocations**, each given only the inputs listed above in its prompt — never simulated inline in the same context as Architect Council or each other. An evaluator that can see its own upstream reasoning anchors on it; this is the same Independence Rule already adopted in the `tom-auditor` skill (an auditor can't grade its own defense). Skipping this and role-playing all seven perspectives in one pass produces a softer Red Team and a disguised-variant Alternative every time — that failure mode is exactly what this framework exists to prevent.

## Mandatory 9-section deliverable

Fill every section of `docs/architecture/adr/TEMPLATE_ADR_REVIEW.md`, in order:

1. **Problem Statement**
2. **Current Repository** — how ACC currently works, evidence only (`file:line` citations), no interpretation
3. **Independent Review Proposal** — exactly what's recommended, no hedging
4. **Architect Council** — best possible defense
5. **Red Team** — attack on assumptions / scalability / uniqueness / maintainability / production behavior
6. **Alternative Architecture Team** — a different first principle, not a variant
7. **Systems Review Board** — scored table, both proposals, all 8 criteria from the config
8. **Council Decision** — Accept / Reject / Hybrid, reasons, explicit Constitution Guardian reconciliation
9. **Actionable Implementation Plan** — dependencies, milestones, tests, migration

**No Implementation Plan may be written before section 8 is decided.** If section 8 is Reject, section 9 is replaced with "No implementation — proposal rejected," plus, if applicable, what would need to change to reopen the question. Debating architecture inside section 9 is out of scope — that debate is sections 4–8; section 9 executes a decision that's already been made.

## Evidence discipline

Same standard as `tom-auditor`: the `Current Repository` section is evidence-driven — `file:line` citations for every claim about how the system currently works, not general/remembered knowledge of the codebase. Re-verify citations at review time rather than reusing citations from a prior pass or a prior conversation, since the repo may have changed.

## Constitution Guardian required reading

| Document | Path |
|---|---|
| Constitution | `PROJECT_CONSTITUTION_V4.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Enforcement spec | `docs/ARCHITECTURE_ENFORCEMENT.md` |
| Workspace vision | `docs/architecture/WORKSPACE_VISION.md` |
| Transition plan | `docs/architecture/ARCHITECTURE_TRANSITION_PLAN.md` |
| Agent directives | `AGENTS.md` |

## Output location and numbering

Existing ADRs occupy `ADR-001` through `ADR-013` in `docs/architecture/adr/`, in a `Status / Date / Deciders / Supersedes / Related` header style followed by `Context / Decision / Rationale`. **Note a pre-existing numbering collision unrelated to this framework:** two files both claim `ADR-007` (`ADR-007_PROVIDER_REGISTRY.md` and `ADR-007_APPSTATE_NOTIFICATION_STORMS.md`) — flag this for cleanup separately; don't let it block new numbering.

New Architecture Decision Reviews continue the sequence starting at **ADR-014**, using the same header block as existing ADRs, with the 9-section adversarial body appended below `Rationale`. Six ADRs are pre-seeded in the config (`docs/agents/adr-review-config.json`) as ADR-014 through ADR-019 — confirm no other in-flight work has already claimed those numbers before writing the file (a separate track referenced "ADR-015/016/017" informally earlier in this project's history for an unrelated state-authority decision; verify those aren't real files elsewhere before reusing the numbers).

## Pre-publish self-check

1. Confirm Red Team, Alternative Architecture Team, and Constitution Guardian were run as genuinely separate Agent invocations, not simulated — name each subagent's session/output in the document so it's auditable later.
2. Confirm `Current Repository` cites `file:line` evidence, not general knowledge.
3. Confirm the Alternative Architecture Team's proposal is materially different from the reviewed proposal — same test Tom uses for a "different attack vector," not a restated one.
4. Confirm Council Decision explicitly reconciles the Constitution Guardian's finding, even when the finding is "no conflict."
5. Confirm no Implementation Plan exists for a Rejected proposal.
6. Confirm the ADR number wasn't already claimed (see Output location and numbering).
