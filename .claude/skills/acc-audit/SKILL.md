---
name: acc-audit
description: Use to dispatch ACC review work to the existing Tom implementation auditor or the ADR review framework instead of inventing a competing audit process. Triggers on: audit, verify implementation, architecture-compliance review, or ADR decisions.
---

# ACC Audit Dispatch

Use this skill to select the existing ACC review framework rather than creating a competing audit process.

## Implementation compliance

Use `.agents/skills/tom-auditor/SKILL.md` for implementation and architecture-compliance audits of work already written against an approved direction.

## Architecture decisions

Use `.agents/skills/adr-review/SKILL.md` when the question is whether ACC should choose or reopen a significant architectural direction.

## Rules

- Do not simulate Tom's or ADR Review's independent roles inline when their skills require separate Agent invocations.
- Do not declare implementation complete merely because tests or documentation look good.
- Treat the referenced skill files and their authority configs/templates as the source of truth.
