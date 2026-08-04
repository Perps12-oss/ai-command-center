# Tom Audit — R1 State Authority Mutate Track (ADR-015 → ADR-017)

**Auditor:** Tom (Senior Engineering Auditor)  
**Date:** 2026-08-04  
**Baseline:** `origin/main` @ `aee093c` (merge #151 ADR-017)  
**Scope:** End-to-end SA.mutate track delivered by implementing cloud agents — docs closeout (#145), ADR-015 Memory (#146), ADR-016 Goals (#149), ADR-017 WEA disposition (#151)  
**Authority config:** `docs/agents/tom-implementation-auditor.json`  
**Motto:** Trust code. Verify behavior. Challenge assumptions. Approve only what is actually implemented.

---

## Executive Summary

Audited the R1 State Authority mutate closeout from soft-shadow stop-line through ADR-015/016/017. **Code and pin tests match the accepted ADRs:** live `SA.mutate` is WM nodes/edges + `store_memory` + `submit_goal`; workflows/executions/agents are rejected; Memory and Goals writes go through injected SoT callbacks (not SA→repo direct, not WM dual-write). **23 scoped pin tests passed** in this environment; UCGS PASS.

Verdict is **COMPLIANT** for the declared R1 SA.mutate track. Top risks are **documentation residue** (stale “mutate stub / goals deferred / mutate deepen gated” lines that contradict the closed stop line) and an intentional **composition-root DI soft dual** vs AGENTS.md Rule 3 (sync callbacks for receipts — documented in ADR-016). Neither is a critical architectural violation of the accepted mutate ADRs. Optional extensions (memory delete, goals lifecycle, WEA read projection) remain correctly **not shipped**.

---

## Scores and status

```
Overall Score: 91
Status: COMPLIANT
Implementation Maturity: LEVEL_4 (Production quality for declared mutate surface;
  platform-level SA aggregation for WEA not in scope)
```

### ACC final verdict block

```
Constitution Compliance:     PASS
Architecture Compliance:     PASS
Primitive Reuse Compliance: PASS (N/A for UI primitives — no UI surface in this track)
CustomTkinter Compliance:    PASS (N/A — no UI rewrite; headless SA/services only)
AppState Compliance:         PASS (memory/goals publish bus facts → AppState reducers)
GitHub Pattern Compliance:   PASS (callback SoT mirrors prior soft-shadow pattern)
```

---

## Dimension scores (weighted)

| Dimension | Weight | Score | Justification |
|-----------|--------|------:|---------------|
| architecture_compliance | 20 | 94 | SA owns mutate contract; SoT callbacks; no GoalRepo in SA; WEA out |
| plan_adherence | 15 | 90 | Stop line + ADR-015/016/017 met; stale checklist residues deduct |
| implementation_completeness | 15 | 95 | Declared surface complete; optional work correctly excluded |
| code_quality | 15 | 90 | Clear op branches, receipts, validation; small factory lookup quirk |
| maintainability | 10 | 88 | Soft duals documented; stale docs hurt future agents |
| scalability | 5 | 85 | Sync mutate OK today; async EventBus still gated elsewhere |
| testability | 5 | 95 | Strong soft-shadow + ADR-017 pins |
| ui_consistency | 5 | 100 | No UI redesign in track |
| performance | 5 | 85 | Not a perf track; goals mutate may cascade plan — documented |
| technical_debt | 5 | 80 | Soft duals + doc drift + `_goal_lookup` workspace stamp |

**Weighted overall ≈ 91.**

---

## Mandatory ACC questions

1. **Reuse primitives?** N/A for Inspector/Timeline — track is services/SA. Reuses existing MGS / scheduler / WM.
2. **Duplicate functionality?** Soft dual **entry points** (tool `memory.store`, `GOAL_SUBMIT_REQUEST`) into **same SoT** — intentional per ADRs, not dual stores.
3. **Match approved ACC design?** Yes — contract + ADR-015/016/017.
4. **AppState driven?** Writes publish `MEMORY_STORED` / `GOAL_*`; UI still AppState projection (R4).
5. **CustomTkinter native?** Untouched.
6. **Repository patterns?** Factory DI + services + repos; SA does not own storage.
7. **Scale without rewrite?** Yes for declared surface; WEA mutate would need new ADR.
8. **Senior prod review?** Approve mutate track; require doc hygiene follow-up.

---

## Architecture Compliance

**PASS.**

Evidence:

- Supported ops: `ai_command_center/services/state_authority_service.py:64-77` — WM + `store_memory` + `submit_goal` only.
- Memory mutate (`:383-413`) calls `_memory_store` only; no `WorldModel.apply` on that branch.
- Goals mutate (`:349-382`) calls `_goal_submit` only; SA has no `GoalRepository` import (forbid text only at `:317`).
- Factory wires (`service_factory.py:262-269`): `memory_store=memory_graph.store_memory`, `goal_submit=goal_scheduler.submit_goal_for_state`.
- Scheduler helper (`goal_scheduler_service.py:129-167`) calls `self.submit_goal(goal)` — same SoT as bus intake (`:306`).

**Rule 3 tension (documented, accepted):** SA invokes bound service callables synchronously for receipted mutate. ADR-016 rejected bus-only publish as receipt-less. Composition root injects callbacks — not ad-hoc peer imports inside unrelated services.

---

## Plan Adherence

**PASS with hygiene debt.**

| Plan artifact | Agent delivery | Match? |
|---------------|----------------|--------|
| Stop line next gate → Memory ADR | #146 ADR-015 | ✅ |
| Next → Goals via scheduler | #149 ADR-016 | ✅ |
| Next → WEA each needs ADR | #151 ADR-017 disposition (remain outside) | ✅ |
| Combined ADR+code PRs | 015/016 yes; 017 docs+pins | ✅ |
| Soft-shadow 4d / 3c / 5c/6c | Code + inventories | ✅ |

**Doc CONFLICTS (do not treat docs as sole truth):**

| Location | Stale claim |
|----------|-------------|
| `STATE_AUTHORITY_CONTRACT.md:191` | Still says `mutate` stub |
| `STATE_AUTHORITY_CONTRACT.md:195` | “goals/workflows still deferred” after ADR-016 |
| `MEMORY_SOFT_SHADOW_INVENTORY.md:114` | “Goals … mutate still deferred” |
| `PHASE_R1_RUNTIME_RECONCILIATION.md:185` | “mutate deepen gated” vs stop line CLOSED |
| `PHASE_R1…:189` | “See stop line for the next hard gate” — stop line now closed |

---

## Repository Pattern Adherence

**PASS.** Matches Stage 2 soft-shadow pattern: inventory → ADR → factory wire → pin tests → stop line / matrix update. Pre-flights present for ADR-015/016/017.

---

## Implementation Findings

### What is actually implemented

1. `SA.mutate(store_memory)` → MGS → `memory_nodes` + `MEMORY_STORED` + receipt  
2. `SA.mutate(submit_goal)` → scheduler → `goals` + `GOAL_SUBMITTED` (+ activate/plan cascade) + receipt  
3. WEA ops unsupported (generic reject)  
4. Soft duals retained by design (tools / `GOAL_SUBMIT_REQUEST`)

### Partial / non-scope (correct)

- Memory delete via SA  
- Goals pause/resume/cancel via SA  
- WEA mutate or read-only SA projection  
- GoalEngine schema cleanup  
- Async EventBus / Goose / Predictive re-wire  

### Line-level findings

| Sev | Finding | Evidence |
|-----|---------|----------|
| Med | Stale contract next-steps contradict CLOSED banner | `STATE_AUTHORITY_CONTRACT.md:191,195` vs `:1-8` |
| Med | MEMORY inventory goals row stale | `MEMORY_SOFT_SHADOW_INVENTORY.md:114` |
| Low | R1 program exit wording vs stop line | `PHASE_R1…:185,189` |
| Low | `_goal_lookup` stamps workspace_id without filtering | `service_factory.py:248-257` |
| Info | Goals mutate can cascade `PLAN_REQUEST` | `goal_scheduler_service.py:127` + ADR-016 cascade note |
| Info | AGENTS Rule 3 vs sync DI callbacks | ADR-016 decision; factory bind |

---

## Code Quality Findings

- Op dispatch is explicit and receipt-oriented.  
- Empty body/title rejected.  
- Pin tests assert no `WORLD_MODEL_MUTATION_APPLIED` for memory/goals mutate.  
- ADR-017 pin locks `_SUPPORTED_OPS` against WEA op names (`tests/test_adr017_sa_mutate_disposition.py`).

---

## Technical Debt

1. Soft dual entry points (acceptable debt if inventories stay honest).  
2. Doc residue after multi-ADR closeout (agent hygiene failure).  
3. Goal projection workspace scoping incomplete in lookup helper.

---

## Deficiencies

**None critical** for the declared mutate track.

**Non-critical:** documentation drift listed above; `_goal_lookup` workspace stamp.

---

## Partially Implemented Features

None within ADR-015/016/017 acceptance criteria. Optional stop-line items are explicitly out of scope — do **not** score as incomplete delivery of this track.

---

## Features Requiring Redesign

None. Do **not** redesign WEA into SA.mutate without a superseding ADR proving single-SoT callbacks.

---

## Evidence

**Ran:**

```text
pytest (memory/goals/WEA/ADR-017/shadow goals pins): 23 passed
UCGS: PASS
```

**Read (non-exhaustive):**

- `state_authority_service.py`, `service_factory.py`, `goal_scheduler_service.py`, `memory_graph_service.py`  
- ADR-015/016/017, stop line, contract, SHADOW, MEMORY/GOALS/WEA inventories  
- Pin tests under `tests/test_*_sa_soft_shadow.py`, `tests/test_adr017_sa_mutate_disposition.py`  
- Merge history: #145 → #146 → #149 → #151 on `main`

**Not claimed as proof:** commit messages alone; UI screenshots (N/A).

---

## Risk Assessment

| Horizon | Risk | Mitigation |
|---------|------|------------|
| Short | Future agents re-open WEA mutate from stale “deferred” wording | Fix doc residue; trust ADR-017 + pin tests |
| Short | Goals mutate triggers planning cascade unexpectedly | Documented; callers must understand scheduler ownership |
| Long | Soft duals drift into true dual stores | Keep inventories + Tom pins; forbid repo-direct |
| Long | Rule 3 vs DI callbacks uncodified beyond ADR | Optional ADR/constitution note on receipted SA DI |

---

## Next actions (ordered)

1. **Doc hygiene PR (small):** Fix `STATE_AUTHORITY_CONTRACT.md` next-steps items 2/6; MEMORY inventory Goals row; PHASE_R1 exit “mutate deepen gated” / “next hard gate” lines to match stop line CLOSED.  
2. **Optional:** Filter `_goal_lookup` by workspace when goals gain durable workspace fields.  
3. **Do not start** WEA mutate, Async EventBus, Goose, or Predictive re-wire without their gates.  
4. Retire this implementing agent after hygiene (optional) or immediately — mutate track is merge-complete on `main`.

---

## Final Verdict

```
Overall Score: 91
Status: COMPLIANT
Implementation Maturity: LEVEL_4

Constitution Compliance:     PASS
Architecture Compliance:     PASS
Primitive Reuse Compliance: PASS (N/A UI primitives)
CustomTkinter Compliance:    PASS (N/A)
AppState Compliance:         PASS
GitHub Pattern Compliance:   PASS
```

**Tom approves the R1 SA.mutate implementation track as matching accepted ADRs and stop-line intent.** Documentation residue must not be mistaken for unfinished mutate work. Optional tracks remain gated elsewhere.
