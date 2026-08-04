# Constitutional Pre-Flight — Goals 3b ADR (Phase-9 disposition)

**Date:** 2026-08-03  
**Branch:** `cursor/goals-3b-adr-6855`  
**Baseline:** `origin/main` @ `e9d0c15`

## This run’s continuity (do not lose)

| Track | Artifact | Disposition |
|-------|----------|-------------|
| Slice 4 parallel PR | [#127](https://github.com/Perps12-oss/ai-command-center/pull/127) @ `a6ace2a` | Superseded by #125; **please close manually** (close API 403 here) |
| Edge mutate / quarantine | On `main` via #125/#126 | Not re-done |
| Dual-path inventory | Restored into `state_authority/GOALS_DUAL_PATH_INVENTORY.md` | Kept |
| `mutation_for_edge` DELETE helper | Small WM salvage from #127 | Optional code in this PR — **not** goals schema |

## Authority read
- [x] `PROJECT_CONSTITUTION_V4.md`
- [x] ADR-006 / ADR-005
- [x] `SHADOW_SOT_INVENTORY.md` step 3b
- [x] `STATE_AUTHORITY_CONTRACT.md`

## Scope
- Publish **ADR-012** (Proposed): retire vs merge Phase-9 GoalEngine — **human decision required**
- Point inventory docs at ADR-012
- Restore dual-path inventory from this run’s #127 work
- Optional: fold WM `mutation_for_edge` DELETE helper + endpoint test (no goals tables touched)

## Out of scope
- Deleting `goal_engine_goals` or Phase-9 modules  
- Re-wiring GoalEngine onto intake  
- `SA.mutate` for goals  
- Memory / workflows SA routing  
- Goose / Async EventBus / Mission Control  

## Verdict
**GO** (docs + optional WM helper only)
