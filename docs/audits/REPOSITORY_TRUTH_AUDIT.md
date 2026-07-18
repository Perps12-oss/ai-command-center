# Repository Truth Audit — All Branches

**Date:** 2026-07-18  
**Baseline:** `origin/main` @ `d0bb2ed` (includes GraphCanvas #78)  
**Governance:** `docs/governance/PHASE_COMPLETION_RULE.md`

---

## Main missing Phase 11 deliverables (before integration)

| Feature / audit | On main? |
|-----------------|----------|
| 11A–11D workspaces | Yes |
| BaseGraphCanvas / PrimAudit | Yes (#78) |
| 11E Approval Center panels | **No** |
| 11F Goal Dashboard panels | **No** |
| Article 18 `surface_state` | **No** |
| `GOAL_AMBER` / `WORLD_TEAL` in UI Constitution | **No** |
| PHASE_11_REMEDIATION_AUDIT / PLACEHOLDER_AUDIT | **No** |
| Verify PHASE_11F | **No** |

---

## Non-merged / active remote branches

| Branch | Feature (vs main orphans) | Merged? | Superseded? | Action |
|--------|---------------------------|---------|-------------|--------|
| `cursor/cloud-agent-1784344178346-8nt9j` | 11E, 11F, Art.18, constitution tokens, remediation/placeholder audits, Verify11F | **no** | **no** | **merge** (via `phase-11-final-integration`) |
| `cursor/primitive-reuse-graph-canvas-f0ab` | none missing from main (content in #78 squash) | content yes / tip commits no | tip **yes** | delete after confirming #78 |
| `phase-11a-command-center` | no Phase-11 orphans vs main (early tip) | no (PR #75 OPEN) | **yes** | close PR #75; **delete** |
| `phase13-execution-inspector` | no Phase-11 orphans | no | mostly | review then delete |
| `feature/timeline-undo-handlers` | no Phase-11 orphans | content via #74 | tip stale | review then delete |
| `cursor/timeline-undo-p1-6c6b` | no Phase-11 orphans | no (PR #66 OPEN) | **yes** | close #66; delete |
| `cursor/plugin-catalog-entities-6c6b` | no Phase-11 orphans | no | **yes** (stale) | review then delete |
| `cursor/reasoning-loop-pr1-4-b0b8` | no Phase-11 orphans | no | **yes** (stale) | review then delete |
| `feat/program4-slice4-context-plugin-entities` | no Phase-11 orphans | no | **yes** (stale) | review then delete |
| `feature/p4-workflow-ux-complete` | no Phase-11 orphans | content via #70 | tip stale | delete |
| `feature/phase7-ari-update` | no Phase-11 orphans | no | **yes** | review then delete |
| `feature/planner-evolution-phase-c0-constitution` | no Phase-11 orphans | no | planner WIP | keep only if still planned; else delete |
| `cursor/automation-workspace-pr14-15-6c6b` | — | yes (0 ahead) | **yes** | delete |
| `cursor/execution-event-pr8-6c6b` | — | yes (0 ahead) | **yes** | delete |
| `cursor/ui-backlog-p2-p3-6c6b` | — | yes (0 ahead) | **yes** | delete |
| `cursor/pragmatic-extensibility-docs-7d9d` | — | yes (0 ahead) | **yes** | delete |
| `feature/vnext-state-driven-blueprint` | — | yes (0 ahead) | **yes** | delete |

### Other “11E/11F situations”?

**Only one High orphan set:** `cursor/cloud-agent-1784344178346-8nt9j` holds Phase 11E/11F + Article 18 + audits absent from `main`.

No other remote branch contains those Phase 11 closeout artifacts. Remaining stale branches are non–Phase-11 debt (delete/review), not competing phase truths.

---

## Integration action

Branch: `phase-11-final-integration`  
Start: `origin/main` (`d0bb2ed`)  
Merge: `8b11052` (closeout tip)  
Conflict policy: keep **BaseGraphCanvas** World Model graph; preserve Article 18 empty copy.
