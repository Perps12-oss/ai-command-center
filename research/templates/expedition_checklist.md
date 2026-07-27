# Expedition Checklist

Use this checklist for every repository investigation.

## Before starting

- [ ] Register repository in `research/repositories/index.md`
- [ ] Create `research/repositories/{expedition-id}-{repo-name}/`
- [ ] Assign expedition owner and expected date

## Investigation

- [ ] Clone or locate source code
- [ ] Read high-level architecture and entry points
- [ ] Fill `repository/repository_template.md` as `report.md`

## Pattern extraction

- [ ] Extract engineering ideas as pattern candidates
- [ ] Store candidates in the repository folder
- [ ] Validate each candidate with `pattern/pattern_validation_template.md`
- [ ] Promote validated patterns to `research/patterns/index.md` as `PAT-NNN`

## Decision and next steps

- [ ] Record research decision as `RD-NNN`
- [ ] Update `research/decisions/index.md`
- [ ] Produce comparison matrix if multiple repositories are involved
- [ ] Draft integration proposals where appropriate
- [ ] Submit integration proposals for Architecture Review (Tom)
- [ ] Update `research/index.md` with links to RD, patterns, and ADRs

## Final checks

- [ ] No code copied without understanding
- [ ] No prescriptive architecture recommendations outside ADR process
- [ ] All artifacts link back to ACC authority model
