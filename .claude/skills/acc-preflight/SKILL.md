---
name: acc-preflight
description: Use before any ACC implementation work to produce the Constitutional Pre-Flight required by PROJECT_CONSTITUTION_V4 Article X. Triggers on: starting implementation, changing architecture-sensitive code, or when asked for a pre-flight.
---

# ACC Pre-Flight

Use this skill before implementation work when the repository governance requires a Constitutional Pre-Flight.

## Procedure

1. Read `PROJECT_CONSTITUTION_V4.md`.
2. Read `AGENTS.md`.
3. Read the applicable architecture documentation.
4. Identify relevant contracts, ADRs, approved plans, phase rules, and tests.
5. Establish the repository evidence baseline with file/path references.
6. Produce the required Constitutional Pre-Flight before implementation begins.

Do not reproduce the Constitution or `AGENTS.md` in this skill.

Follow their current contents as the source of truth.

If the task is a major unresolved architecture decision rather than implementation against an established direction, stop and use `.agents/skills/adr-review/SKILL.md`.
