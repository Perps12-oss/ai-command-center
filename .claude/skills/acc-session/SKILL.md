---
name: acc-session
description: Use to write or resume an ACC continuity checkpoint under docs/checkpoints/ across LLM sessions. Triggers on: checkpoint, resume work, session handoff, or ending a substantial work session.
---

# ACC Session Continuity

Use this skill to preserve and resume project work across LLM sessions.

## Canonical location

Shared continuity belongs under `docs/checkpoints/` so Cursor, Devin, Claude, auditors, and other LLMs can consume it.

## Checkpoint rules

A checkpoint records only verified or explicitly labelled current work state.

Include, where relevant:

- objective and scope
- approved baseline
- completed work
- current repository/branch state
- verified tests and failures
- unresolved blockers
- relevant files
- exact next action

Never use a checkpoint as a substitute for source code, the Constitution, architecture, contracts, ADRs, or tests.

Do not invent progress. Mark uncertain or unverified information explicitly.

## Resume procedure

1. Read `docs/checkpoints/CURRENT.md` if it exists.
2. Verify its claims against the current Git state and repository evidence.
3. Re-read authoritative documents relevant to the current task.
4. Reconcile stale checkpoint information rather than blindly trusting it.
5. Continue only from the verified state.

## Checkpoint procedure

Before ending a substantial work session or when asked to checkpoint:

1. Inspect current Git state.
2. Record only verified progress.
3. Record failures/blockers and the exact next action.
4. Update `docs/checkpoints/CURRENT.md`.
