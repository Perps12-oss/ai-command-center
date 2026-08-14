# Constitutional Pre-Flight — P1 Remediation (UCGS / SQLite / Execution)

**Status:** ACTIVE  
**Date:** 2026-08-12  
**Authority:** PROJECT_CONSTITUTION_V4.md  
**Evidence:** `docs/audits/P1_NARROW_PASS_UCGS_SQLITE_EXECUTION.md` (PR #169); Independent Verification Audit conclusions as restated therein  
**Branch intent:** `cursor/p1-remediation-*`

## Scope

Implement confirmed P1 blockers then remaining independently verified findings. Not a redesign.

| P1 | Contract |
|----|----------|
| A | UCGS CI must evaluate PR/push range diffs; staged remains local |
| B | Shared SQLite: one context cannot commit another's txn |
| C | ACTION_INVOKE must not bypass receipted execution |
| D | workspace_execute_command under same LAUNCH_TOOL policy as shell |

## Invariants affected

- Art. II verification must not create false confidence (UCGS)
- Storage ownership / persistence integrity (SQLite)
- ADR-018 sole TOOL_INVOKE publisher + receipt boundary (ActionRegistry path)
- Permission boundary for shell-equivalent capabilities

## Non-goals

Disproved mechanisms (`id(conn)` instability, alias→TOOL_INVOKE, drop-path recursion). No UI redesign. No new parallel executors.

## Sequence

1. UCGS CI + negative tests  
2. SQLite connection-owned serialization  
3. ACTION_INVOKE → canonical boundary  
4. workspace_execute_command permission  
5. Remaining verified findings + docs + ledger  

Implementation may begin.
