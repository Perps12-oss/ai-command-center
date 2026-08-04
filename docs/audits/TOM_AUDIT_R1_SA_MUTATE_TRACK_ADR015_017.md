# Tom Audit (REVISED) — R1 State Authority Mutate Track (ADR-015 → ADR-017)

**Auditor:** Tom (Senior Engineering Auditor)  
**Revision:** 2 — adversarial re-audit after methodological challenge of v1  
**Date:** 2026-08-04  
**Baseline:** `origin/main` @ `aee093c` (merge #151 ADR-017)  
**Scope:** SA.mutate track delivered by implementing agents (#145–#151)  
**Authority:** `docs/agents/tom-implementation-auditor.json`  
**Motto:** Trust code. Verify behavior. Challenge assumptions. Approve only what is actually implemented.

> **Supersedes v1 of this report.** v1 scored 91 COMPLIANT with decorative PASSes, backwards citations, and no edge-case pushback. That verdict is withdrawn.

---

## Executive Summary

Re-audited the R1 SA.mutate track with adversarial probes, not pin-test cheerleading.

**What still holds:** ADR-015/016 wiring is real — factory-injected SoT callbacks, no `GoalRepository` import in SA, `store_memory`/`submit_goal` branches do not call `WorldModel.apply`. Enumerated soft-shadow pin suite is **23 collected / 23 passed** (recomputed this run; list below — not copy-forwarded).

**What v1 missed:**

1. **Scheduler queue corruption** — `submit_goal` with a repeated `goal_id` while another goal is active appends the same id twice to `_queue` (runtime probe). SA.mutate exposes this path; **no pin covers it**.
2. **SA can still invent WM `type=memory` nodes** via `create_node` — parallel to `memory_nodes` SoT. ADR-015 forbids dual-write *from* `store_memory`; it does **not** stop callers using WM mutate as a fake memory graph. Probe shows both surfaces in one `query`.
3. **Partial-apply / malformed-body / unbound-callback / plan-cascade** paths exist in code and runtime but are thinly or not pinned.
4. **Doc residue** remains (secondary).

**Verdict:** **PARTIALLY_IMPLEMENTED** for production-hardening of the mutate surface. Governance stop-line “CLOSED” is a **plan/disposition** claim, not a production DoD. Do **not** equate this track with PERF’s “Closed” bar (PERF withheld Closed pending ARM64 soak). This track has **no equivalent soak / adversarial gate** stated in the ADRs.

---

## Scores and status

```
Overall Score: 74
Status: PARTIALLY_IMPLEMENTED
Implementation Maturity: LEVEL_3 (Feature connected + ADR-aligned; not production-hardened)
```

### ACC final verdict block

```
Constitution Compliance:     PASS (no UI/repo bypass found for this track)
Architecture Compliance:     PASS WITH FINDINGS (SoT callbacks OK; queue dup + WM memory footgun)
Primitive Reuse Compliance:  N/A (no Inspector/Timeline surface in this track — not scored PASS)
CustomTkinter Compliance:    N/A (no UI changes — not scored PASS)
AppState Compliance:         PASS (bus facts MEMORY_STORED / GOAL_* still feed reducers)
GitHub Pattern Compliance:   PASS (factory DI + soft-shadow pins match Stage 2 pattern)
```

N/A rows are **not** green PASSes. They do not inflate the score.

---

## What “23 pin tests” means (recomputed)

Command (this environment, 2026-08-04):

```bash
APPDATA=/tmp/tom_adversarial python3 -m pytest \
  tests/test_memory_sa_soft_shadow.py \
  tests/test_goals_sa_soft_shadow.py \
  tests/test_adr017_sa_mutate_disposition.py \
  tests/test_workflows_sa_soft_shadow.py \
  tests/test_executions_sa_soft_shadow.py \
  tests/test_agents_sa_soft_shadow.py \
  tests/test_shadow_sot_goals.py \
  -v --no-cov
# collected 23 items — 23 passed in 0.44s
```

| # | Test |
|---|------|
| 1 | `test_memory_sa_soft_shadow::test_build_services_wires_memory_lookup_for_state` |
| 2 | `…::test_lookup_for_state_does_not_publish_memory_bus_events` |
| 3 | `…::test_sa_query_include_memories_uses_lookup` |
| 4 | `…::test_sa_mutate_store_memory_round_trip` |
| 5 | `…::test_sa_mutate_store_memory_rejects_empty_body` |
| 6 | `…::test_sa_mutate_still_rejects_workflow_style_goal_lifecycle` |
| 7 | `test_goals_sa_soft_shadow::test_build_services_wires_goal_submit_for_state` |
| 8 | `…::test_sa_mutate_submit_goal_round_trip` |
| 9 | `…::test_sa_mutate_submit_goal_rejects_empty_title` |
| 10 | `…::test_sa_mutate_still_rejects_create_goal_alias` |
| 11 | `test_adr017_sa_mutate_disposition::test_sa_supported_ops_excludes_wea_domains` |
| 12–14 | workflows soft-shadow (wire / no lookup / reject `start_workflow`) |
| 15–18 | executions soft-shadow (wire / no lookup / reject / correlation) |
| 19–21 | agents soft-shadow (wire / no lookup / reject `spawn_agent`) |
| 22–23 | `test_shadow_sot_goals` (no GoalEngine / goal_lookup projects repo) |

Coincidence with another track’s “23” is possible; **this 23 is enumerated and re-run**. It is also a **narrow** suite: happy-path round-trips + reject pins. It is **not** adversarial coverage.

---

## What UCGS is

**UCGS** = Unified Constitutional / Architecture Governance System (project tooling).

- Runner: `python3 tools/ucgs_runner.py` → `.ucgs_last.yaml`  
- Gate: `python3 tools/ucgs_ci_gate.py .ucgs_last.yaml`  
- Config: `ucgs.config.yaml` + `ucgs.profiles/ai-command-center.yaml`  
- Checks (this profile): layer imports, forbidden patterns, large commit, contract drift  
- CI workflow: `.github/workflows/ucgs.yml`

UCGS PASS means **no S4/S5 / FAIL verdict on that static gate** — it does **not** prove mutate semantics, queue integrity, or dual-SoT absence. v1 treated UCGS as if it validated the mutate design. It does not.

---

## Dimension scores (weighted)

| Dimension | Weight | Score | Justification |
|-----------|--------|------:|---------------|
| architecture_compliance | 20 | 78 | Callback SoT correct; queue dup + WM `type=memory` footgun |
| plan_adherence | 15 | 82 | ADRs implemented; stop-line CLOSED ≠ prod DoD; stale docs |
| implementation_completeness | 15 | 70 | Happy path yes; edge paths untested / broken |
| code_quality | 15 | 72 | Clear branches; silent overwrite + queue append bug |
| maintainability | 10 | 70 | Soft duals + doc drift + two memory graphs via SA |
| scalability | 5 | 65 | Sync mutate + plan cascade; no concurrency story |
| testability | 5 | 68 | Pins exist but miss probes below |
| ui_consistency | 5 | — | **N/A — excluded from weighted average** |
| performance | 5 | 70 | Not soak-tested; cascade cost unknown |
| technical_debt | 5 | 65 | Soft duals + queue bug + WM memory alias |

**Weighted (excluding N/A ui_consistency, redistributing its 5 into architecture/completeness conceptually): ≈ 74.**

---

## Load-bearing claims — with citations (v1 failed this)

### Claim: no SA → GoalRepository direct

**Evidence:** AST of `ai_command_center/services/state_authority_service.py` — zero `repositories` imports. Write path is callback only:

```360:367:ai_command_center/services/state_authority_service.py
                    ok_submit, submit_msg, meta = self._goal_submit(
                        title,
                        workspace_id=delta.workspace_id,
                        description=str(raw.get("description") or "").strip(),
                        priority=str(raw.get("priority") or "").strip(),
                        goal_id=str(raw.get("goal_id") or "").strip(),
                        correlation_id=correlation.correlation_id,
                    )
```

Factory bind:

```262:269:ai_command_center/core/service_factory.py
    state_authority = StateAuthorityService(
        bus,
        world_model,
        memory_lookup=memory_graph.lookup_for_state,
        memory_store=memory_graph.store_memory,
        goal_lookup=_goal_lookup,
        goal_submit=goal_scheduler.submit_goal_for_state,
    )
```

Scheduler same SoT as bus intake:

```167:167:ai_command_center/services/goal_scheduler_service.py
        self.submit_goal(goal)
```

### Claim: `store_memory` does not call `WorldModel.apply`

**Evidence:** `_world_model.apply` appears only at lines **436, 463, 489, 516** — all inside node/edge arms **after** the memory/goal branches (`:383-413` memory returns via `applied.append` without apply). Memory branch:

```395:412:ai_command_center/services/state_authority_service.py
                    ok_store, store_msg, meta = self._memory_store(
                        body,
                        workspace_id=delta.workspace_id,
                        entity_id=entity_id,
                    )
                    ...
                    applied.append(
                        {
                            "op": op,
                            ...
                            "memory_id": meta_dict.get("id"),
```

### Claim: WEA ops unsupported

**Evidence:** `_SUPPORTED_OPS` at `:64-77`; reject pins for `start_workflow` / `append_execution_run` / `spawn_agent`. Runtime `sorted(_SUPPORTED_OPS)` =  
`create_edge, create_node, delete_edge, delete_node, store_memory, submit_goal, update_node, upsert_node`.

---

## Adversarial findings (blocking / material)

### F1 — HIGH: duplicate `goal_id` doubles scheduler queue

**Probe:** With an active goal holding the scheduler, two `SA.mutate(submit_goal)` calls with `goal_id='dupq'` both return `ok=True`. In-memory `_queue` contained `['dupq','dupq']`; repo title was last-write (`q2`).

**Root:** `submit_goal` always `self._queue.append(queued)` (`goal_scheduler_service.py:120`) with no dedupe; repo `ON CONFLICT` updates the row.

**Why it matters for this track:** ADR-016 made SA a first-class entry into this method. Pins only test first submit happy path.

**DoD gap:** No test; no ADR note; silent corruption risk when callers reuse ids.

### F2 — MEDIUM: SA `create_node` + `type=memory` creates a second “memory” surface

**Probe:** Same mutate batch can `store_memory` (MGS) and `create_node type=memory` (WM). `SA.query` then returns **both** `projection.memories` and WM entities `type=memory`.

**ADR-015** forbids dual-write *inside* `store_memory`. It does **not** remove WM memory-typed nodes from the supported mutate set. Soft-shadow docs call WM memory an “echo”; SA itself can author the echo.

**Untested** in the 23-pin suite.

### F3 — MEDIUM: `submit_goal` mutate triggers live plan cascade

**Probe:** `topics = ['goal.submitted', 'goal.activated', 'plan.request']` on a single mutate while scheduler idle.

Documented in ADR-016 cascade note — but there is **no pin** asserting cascade, and no API warning on `MutationReceipt` that planning has started. Receipt `ok=True` ≠ plan finished.

### F4 — LOW/MED: `_goal_lookup` stamps `workspace_id` without filtering

```248:257:ai_command_center/core/service_factory.py
    def _goal_lookup(*, workspace_id: str = "") -> list[dict]:
        goals = goal_repo.list_goals()
        ...
                    "workspace_id": workspace_id,  # stamp only
```

**Probe:** Query with `workspace_id='OTHER'` still returns goals, all labeled `OTHER`. Projection lies about workspace scope.

### F5 — LOW: partial apply / unbound / malformed body

| Probe | Result | Pinned? |
|-------|--------|---------|
| `body='nope'` (no label/content) | `ok=False`, MGS message | Only empty body pinned |
| Unbound `memory_store` | `ok=False`, “not bound” | No |
| Mixed `store_memory` + `start_workflow` | `ok=False`, `applied=1` (partial) | No |

Behavior is mostly correct; **coverage is not**.

### F6 — LOW: documentation residue (v1’s only “finding”)

Stale lines still claim mutate stub / goals deferred / deepen gated:

- `docs/architecture/STATE_AUTHORITY_CONTRACT.md:191,195`
- `docs/architecture/state_authority/MEMORY_SOFT_SHADOW_INVENTORY.md:114`
- `docs/plans/PHASE_R1_RUNTIME_RECONCILIATION.md:185,189`

Real, but **secondary** to F1–F4.

---

## Closure bar — explicit comparison to PERF

| Track | Code review | Automated pins | Runtime / soak gate | “Closed”? |
|-------|-------------|----------------|---------------------|-----------|
| PERF-001/002 (prior audit) | Pass table | Pins | ARM64 soak **required** before Closed | **Withheld** |
| SA.mutate ADR-015–017 | ADR+merge | 23 happy/reject pins | **None stated** | Stop line marked CLOSED |

**Tom position:** Governance may mark the *ADR/stop-line queue* closed (WEA disposition accepted; no further R1-blocking mutate ADR required). That is **not** the same as production Closed for a state-mutation surface.

Equivalent bar for this track before calling implementation Closed:

1. Pin (or fix) **F1** queue dedupe / reject duplicate `goal_id`  
2. Pin or ADR-clarify **F2** (forbid or document WM `type=memory` via SA as non-SoT)  
3. Pin cascade / partial-apply / malformed body (**F3/F5**)  
4. Doc hygiene (**F6**)  
5. Optional: workspace-honest goal lookup (**F4**)

Until then: **stop-line CLOSED ≠ implementation Closed**.

---

## Mandatory ACC questions (honest)

1. Reuse primitives? **N/A** for Inspector/Timeline.  
2. Duplicate functionality? **Soft dual entries** (tool/bus) into same SoT — OK; **WM `type=memory` vs memory_nodes** — real dual surface via SA (**F2**).  
3. Match approved design? **Mostly** for ADR ops; **F1** violates safe scheduler ownership expectations.  
4. AppState driven? **PASS** for published facts.  
5. CustomTkinter? **N/A**.  
6. Repo patterns? **PASS** factory DI.  
7. Scale without rewrite? **Not yet** — queue dup + cascade need hardening.  
8. Senior prod review? **Approve ADR direction; withhold prod Closed** pending F1/F2 pins or fixes.

---

## Evidence

**Ran:**

- Enumerated 23-pin suite — 23 passed  
- Adversarial Python probes (P1–P10) — outputs captured in audit session (queue dup, WM memory dual, cascade topics, lookup stamp)  
- UCGS: static gate only (defined above)

**Not evidence:** v1 score, commit messages, “track CLOSED” prose, decorative PASS(N/A).

---

## Risk Assessment

| Risk | Sev | If ignored |
|------|-----|------------|
| Duplicate goal_id queue | High | Double activation / confused planning |
| WM memory nodes via SA | Med | Agents treat WM echo as memory SoT |
| Cascade surprise | Med | Mutate callers assume local write only |
| False CLOSED signal | Med | Retire agent / skip hardening |

---

## Next actions (ordered)

1. **Fix or harden F1** in `SingleGoalScheduler.submit_goal` (dedupe by id / reject conflict) + pin via SA.mutate.  
2. **Pin F2** — either reject `create_node` when `type=memory` through SA, or document+test that WM memory ≠ `memory_nodes`.  
3. Add pins for malformed body, unbound callbacks, partial apply, plan cascade.  
4. Doc hygiene F6.  
5. **Do not retire** the implementing agent’s “all clear” on v1’s COMPLIANT/91; treat this revised audit as the audit of record.  
6. Open/review the audit PR **before** any retirement narrative; `pull/new` is not a reviewed artifact.

---

## Final Verdict

```
Overall Score: 74
Status: PARTIALLY_IMPLEMENTED
Implementation Maturity: LEVEL_3

Constitution Compliance:     PASS
Architecture Compliance:     PASS WITH FINDINGS
Primitive Reuse Compliance:  N/A
CustomTkinter Compliance:    N/A
AppState Compliance:         PASS
GitHub Pattern Compliance:   PASS
```

**Tom withdraws v1 COMPLIANT/91.** ADR wiring is largely real and correctly SoT-callback shaped. Production hardening is **not** done. Stop-line CLOSED is governance disposition only. Highest-priority defect: **duplicate `goal_id` queue append** exposed through SA.mutate.

---

# Addendum — Evidence Q&A (rev 2.1)

**Date:** 2026-08-04  
**Trigger:** Challenge that v2 asserted 74 / labels / Closed without verifiable math and citations.  
**Method:** Answer each item with evidence or revise. Score/labels change only when stated below.

---

## Q1 — Score-74 rubric (visible formula)

Same shape as PERF Tom rev 2 (`docs/audits/TOM_AUDIT_PERF_001_002_FREEZE_CLOSEOUT_2026-08-04.md` on `origin/cursor/tom-audit-perf001-002-30d3`, rubric block “Start at 100”).

**Start at 100.** Deduct only what this audit’s probes/docs support:

| # | Deduction | pts | Maps to |
|---|---|---:|---|
| D1 | F1 — duplicate `goal_id` doubles `_queue` while both mutates return `ok=True` (runtime probe; `goal_scheduler_service.py:118–120` append with no dedupe) | −8 | Correctness / HIGH |
| D2 | F2 — SA still accepts `create_node` with `type=memory` (`_NODE_WRITE_OPS` / `_SUPPORTED_OPS` include `create_node`; no type guard) alongside `store_memory` → dual surfaces in one `query` | −6 | Outcome / SoT clarity |
| D3 | F3 — idle `submit_goal` emits `goal.activated` + `plan.request`; receipt does not surface cascade; unpinned | −3 | Contract honesty |
| D4 | F4 — `_goal_lookup` stamps `workspace_id` without filtering (`service_factory.py:248–257`) | −3 | Projection accuracy |
| D5 | F6 — stale contract / MEMORY / PHASE_R1 lines (see v2 F6) | −2 | Doc honesty |
| D6 | Cited 23-pin suite does **not** exercise F1–F4 failure paths (see Q4) — “23/23 passed” ≠ coverage of findings | −4 | Evidence quality |

**100 − 8 − 6 − 3 − 3 − 2 − 4 = 74.**

No other deductions in this addendum. Classification band: Tom `PARTIALLY_IMPLEMENTED` floor **65** (`docs/agents/tom-implementation-auditor.json` `classification_rules.PARTIALLY_IMPLEMENTED.minimum_score`).

### Weighted dimensions (same 74, shown two ways — not independent corroboration)

Weights from `tom-implementation-auditor.json` `audit_dimensions`.  
Scores below were **chosen so** `Σ(score×weight)/100 = 74` to match the deduction rubric above. They are **not** a second measurement that independently landed on 74.

| Dimension | Weight | Score | Contribution (`w×s/100`) |
|-----------|-------:|------:|-------------------------:|
| architecture_compliance | 20 | 79 | 15.80 |
| plan_adherence | 15 | 81 | 12.15 |
| implementation_completeness | 15 | 70 | 10.50 |
| code_quality | 15 | 75 | 11.25 |
| maintainability | 10 | 72 | 7.20 |
| scalability | 5 | 74 | 3.70 |
| testability | 5 | 60 | 3.00 |
| ui_consistency | 5 | 74† | 3.70 |
| performance | 5 | 74 | 3.70 |
| technical_debt | 5 | 60 | 3.00 |
| **Σ** | **100** | — | **74.00** |

† `ui_consistency` was **not evaluated** for this headless SA track. Score 74 is a **neutral fill** so weights still sum to 100 (Tom config assumes all ten dimensions). Do **not** read as UI PASS. Prefer the **deduction rubric** as the authoritative 74.

Arithmetic check:  
`20×79 + 15×81 + 15×70 + 15×75 + 10×72 + 5×74 + 5×60 + 5×74 + 5×74 + 5×60`  
`= 1580 + 1215 + 1050 + 1125 + 720 + 370 + 300 + 370 + 370 + 300 = 7400`  
`7400 / 100 = 74`.

**Errata:** An earlier draft of this weighted table summed to **69** (wrong scores). That draft is superseded by the table above. Same class of slip as mis-counting a pytest suite when omitting a file (see Q3 errata).

**Label change from v2 final block:** Architecture Compliance is no longer a flat “PASS WITH FINDINGS” — see Q2 (process/outcome split). **Overall score remains 74** (rubric unchanged by Q2 labeling).

---

## Q2 — F2 vs compliance table / “no SA→repo direct”

### What ADR-015 actually forbids

```50:52:docs/architecture/adr/ADR-015_STATE_AUTHORITY_MUTATE_MEMORY.md
4. **Hard forbid:** this op must **not** call `WorldModel.apply` or create WM
   nodes/edges for the same fact. WM `type=memory` echoes remain a separate
   orchestration concern — not this SoT.
```

So ADR-015’s hard forbid is scoped to the **`store_memory` op**, not to banning all WM nodes with `type=memory`.

### Structural claims — still true

| Claim | Still true? | Evidence |
|-------|-------------|----------|
| No SA → `GoalRepository` / `MemoryRepository` import | **Yes** | AST: zero `repositories` imports in `state_authority_service.py`; write via `_goal_submit` / `_memory_store` only (`:360–367`, `:395–400`) |
| `store_memory` does not call `WorldModel.apply` | **Yes** | `apply` only at `:436`, `:463`, `:489`, `:516` (node/edge arms) |
| Primitive Reuse (Inspector/Timeline) | **N/A** (v2) — never a PASS for this track | No UI surface |

### Outcome claim — conditional (PERF-style split)

| Axis | Result | Meaning |
|------|--------|---------|
| A — Process / structural (canonical `store_memory` path) | **PASS** | Factory → MGS → `memory_nodes`; no apply on that branch |
| B — Outcome (SA cannot present a second memory-looking mutate surface) | **FAIL / CONDITIONAL** | `create_node` ∈ `_SUPPORTED_OPS` with **no type filter**; probe created WM `type=memory` + MGS memory in one session |

**F2 does not falsify “no SA→repo direct.”**  
**F2 does downgrade Architecture from a single PASS to:**

```
Architecture Compliance:     PASS (structural SoT callbacks) / FAIL-outcome (unguarded WM type=memory via create_node)
```

Same split pattern as PERF rev 2 Constitution axis (process PASS ≠ Closed-DoD PASS).  
**Primitive Reuse stays N/A** — F2 is not an Inspector/Timeline reuse failure; do not upgrade it to PASS.

**Why a “bypass” doesn’t kill the structural PASS:** The bypass is of an *inferred* “only one way to put memory-shaped facts through SA,” not of ADR-015’s literal hard forbid on `store_memory`. The failure is **outcome / product SoT clarity**, scored as D2 (−6), not as “repo direct” or “Primitive Reuse FAIL.”

---

## Q3 — Track-scoped 23 vs PERF suite

### SA mutate suite (this audit) — collected node ids

Command:

```bash
python3 -m pytest \
  tests/test_memory_sa_soft_shadow.py \
  tests/test_goals_sa_soft_shadow.py \
  tests/test_adr017_sa_mutate_disposition.py \
  tests/test_workflows_sa_soft_shadow.py \
  tests/test_executions_sa_soft_shadow.py \
  tests/test_agents_sa_soft_shadow.py \
  tests/test_shadow_sot_goals.py \
  --collect-only -q --no-cov
# → 23 tests collected
```

| # | Node id |
|---|---------|
| 1 | `tests/test_memory_sa_soft_shadow.py::test_build_services_wires_memory_lookup_for_state` |
| 2 | `…::test_lookup_for_state_does_not_publish_memory_bus_events` |
| 3 | `…::test_sa_query_include_memories_uses_lookup` |
| 4 | `…::test_sa_mutate_store_memory_round_trip` |
| 5 | `…::test_sa_mutate_store_memory_rejects_empty_body` |
| 6 | `…::test_sa_mutate_still_rejects_workflow_style_goal_lifecycle` |
| 7 | `tests/test_goals_sa_soft_shadow.py::test_build_services_wires_goal_submit_for_state` |
| 8 | `…::test_sa_mutate_submit_goal_round_trip` |
| 9 | `…::test_sa_mutate_submit_goal_rejects_empty_title` |
| 10 | `…::test_sa_mutate_still_rejects_create_goal_alias` |
| 11 | `tests/test_adr017_sa_mutate_disposition.py::test_sa_supported_ops_excludes_wea_domains` |
| 12 | `tests/test_workflows_sa_soft_shadow.py::test_build_services_wires_workflow_engine_and_persistence` |
| 13 | `…::test_state_authority_has_no_workflow_lookup` |
| 14 | `…::test_sa_mutate_does_not_support_workflow_ops` |
| 15 | `tests/test_executions_sa_soft_shadow.py::test_build_services_wires_execution_run_event_query` |
| 16 | `…::test_state_authority_has_no_execution_lookup` |
| 17 | `…::test_sa_mutate_does_not_support_execution_ops` |
| 18 | `…::test_execution_run_get_by_correlation_correlates_receipts` |
| 19 | `tests/test_agents_sa_soft_shadow.py::test_build_services_wires_agent_runtime_not_coordinator` |
| 20 | `…::test_state_authority_has_no_agent_lookup` |
| 21 | `…::test_sa_mutate_does_not_support_agent_ops` |
| 22 | `tests/test_shadow_sot_goals.py::test_build_services_does_not_wire_goal_engine` |
| 23 | `…::test_state_authority_goal_lookup_projects_goal_repository` |

### PERF files named in the challenge — first collect (incomplete vs PERF Tom)

Challenge listed four globs (omitting metrics). Collecting only those four paths:

```bash
python3 -m pytest \
  tests/test_perf002_inspector_fingerprints.py \
  tests/test_appstate_notify_coalesce.py \
  tests/test_ui_freeze_closeout_fingerprints.py \
  tests/test_runtime_identity.py \
  --collect-only -q --no-cov
# → 20 tests collected
```

**Overlap of node ids (SA 23 ∩ that 20): empty set.**

### Errata — PERF Tom’s “23” does reproduce when the command is copied verbatim

PERF Tom rev 2 Evidence block (`origin/cursor/tom-audit-perf001-002-30d3`,
`docs/audits/TOM_AUDIT_PERF_001_002_FREEZE_CLOSEOUT_2026-08-04.md` ≈L272–278) runs **five** files:

```bash
APPDATA=/tmp/aicc_appdata python3 -m pytest \
  tests/test_perf002_inspector_fingerprints.py \
  tests/test_appstate_notify_coalesce.py \
  tests/test_appstate_notify_metrics.py \   # ← omitted from the challenge list / SA Q3 first pass
  tests/test_ui_freeze_closeout_fingerprints.py \
  tests/test_runtime_identity.py -q --no-cov
```

Re-run verbatim in this environment (2026-08-04): **23 tests collected / 23 passed.**

The 3-test gap was exactly `tests/test_appstate_notify_metrics.py`:

| Node id |
|---------|
| `…::test_notify_metrics_record_listener_fanout` |
| `…::test_notify_skipped_no_listeners_counter` |
| `…::test_notify_skipped_metrics_only_system_snapshot` |

**20 + 3 = 23.** Not an arithmetic slip in the PERF audit count; a **file-list omission** in the cross-check. SA addendum Q3 first pass was wrong to imply PERF’s 23 failed to reproduce.

**SA 23 ∩ PERF exact 23: still empty** (recomputed after including metrics file). Both integers are real; they remain **disjoint suites**.

**What this SA 23 proves:** factory wires, happy-path memory/goals mutate round-trips, empty title/body rejects, WEA op **names** unsupported, GoalEngine absent, and (via ADR-017 pin) that `create_node` remains a supported **op name**.  
**What it does not prove:** F1, F3, F4; and it **anti-covers** F2 outcome (Q4).

---

## Q4 — Pin status of F1–F4

| Finding | Pin status | Evidence |
|---------|------------|----------|
| **F1** duplicate `goal_id` queue | **Unpinned** | No test submits the same `goal_id` twice under a busy scheduler. `rg goal_id` in soft-shadow SA tests only hits receipt field assert / `cancel_goal` reject (`tests/test_goals_sa_soft_shadow.py`, `tests/test_memory_sa_soft_shadow.py:152`). |
| **F2** `create_node type=memory` | **Anti-pinned (locked-in)** — worse than unpinned | See below. |
| **F3** plan cascade | **Unpinned** | No assert on `PLAN_REQUEST` / `goal.activated` in the 23. Round-trip only checks receipt + `query` title (`test_sa_mutate_submit_goal_round_trip`). |
| **F4** workspace stamp | **Unpinned** | `test_state_authority_goal_lookup_projects_goal_repository` uses a hand-built lookup; factory `_goal_lookup` workspace filter never asserted. |

### F2 anti-pin and migration risk (must resolve before “fix F2”)

1. **Green pin encodes the opposite of an F2 fix:**  
   `tests/test_adr017_sa_mutate_disposition.py:13`  
   `assert "create_node" in supported`  
   Any change that removes `create_node` from `_SUPPORTED_OPS` **breaks this currently-green test by design**.

2. **F2 is not “ban create_node”** — it is “unguarded `type=memory` on WM node writes.” A correct fix is likely a **type guard** (reject or remap `type=memory` on SA node ops) while keeping generic `create_node` for other types. That still requires a **new** pin (and updating ADR-017’s intent text if it implied unrestricted node ops).

3. **Production dependency on WM `type=memory` echoes today:**  
   `ai_command_center/services/orchestration_service.py:404–431` builds WM node dicts with `"type": "memory"` for capability `memory.store` / `memory.query` (tool-completion echo path). Soft-shadow inventory documents this as echo, not `memory_nodes` SoT (`MEMORY_SOFT_SHADOW_INVENTORY.md` Path B).  
   Those echoes are **not** necessarily written via `SA.mutate` today (orchestration / runtime path), but they prove the codebase **already relies on WM nodes typed `memory` as a live shape**. Banning that type only inside SA without an inventory of writers risks:
   - splitting “allowed via orchestration, forbidden via SA” without docs, or
   - breaking callers that later route the same echo through SA.

4. **Required before touching F2:**  
   - Inventory all writers of WM `type=memory` (at least orchestration `:404–431`; SA `create_node`; any BrainRuntime path).  
   - Choose disposition: (a) keep WM echo, document+pin that SA `query` must not treat WM memory as `memory_nodes` SoT; or (b) type-guard SA node ops + migrate orchestration off SA if needed; or (c) superseding ADR.  
   - Update/replace the ADR-017 supported-ops pin so it cannot greenwash an SoT contradiction.

**Therefore:** **23/23 passed does not exercise F1, F3, F4**, and for **F2 it actively protects the status quo** that F2 calls an outcome failure. Deduction D6 (−4) covers the coverage gap; F2’s anti-pin is an additional migration hazard, not scored as a separate numeric deduction in 2.1.

---

## Q5 — 74 vs PERF 69: comparable?

**No — not severity-for-severity comparable across tracks.**

| | PERF Tom rev 2 | This SA mutate Tom rev 2 |
|--|----------------|---------------------------|
| Score | **69** | **74** |
| Rubric home | Same Tom weight schema, **different deduction catalog** | D1–D6 above |
| DoD that withholds “Closed” | `PERFORMANCE_CONSTITUTION.md` Art VI soak + Art XV register | Stop-line ADR queue only (Q6) |
| Dominant open defect class | GUI soak unproven + PerfInspector skip broken | Scheduler queue dup + WM memory footgun |

Both use Tom’s 0–100 + `PARTIALLY_IMPLEMENTED` band, but **deductions are track-local**. A reader must **not** infer “SA-mutate is more done than PERF” from 74 > 69.

If a naive cross-track severity map were forced: F1 (−8) ≈ PERF’s S1 skip defect (−8); SA still scores higher mainly because it does not carry PERF’s −7 GUI-timing and −8 Closed-DoD soak deductions — **those axes do not apply to this headless SA track**, not because SA is healthier overall.

**Action:** State in both reports (this addendum; PERF report already implies track-local rubric). No score change solely from comparability.

---

## Q6 — Define “Closed” once, with citations

**Finding:** There is **no single PROJECT_CONSTITUTION definition** of the word “Closed” that both audits share. Tom must not invent one quietly.

### A. Performance track “Closed”

| Source | Text |
|--------|------|
| `PERFORMANCE_CONSTITUTION.md` **Article VI** (≈L160–167) | **Definition of Done** for every performance task: Tests + Benchmarks + **Soak test** + No regression + Telemetry + Docs/ADR |
| `PERFORMANCE_CONSTITUTION.md` **Article XV** (L385–394) | Debt register Status column: PERF-001/002 = **Mitigated** … “Win ARM64 soak **to close**” |

PERF Tom withholds **Art XV Closed** until soak — that is this DoD.

### B. SA.mutate track “CLOSED” (as used by implementing agents)

| Source | Text |
|--------|------|
| `docs/audits/R1_UNGATED_STOP_LINE.md` L18–29 | Heading **“R1 SA.mutate track — CLOSED”** = live mutate surface listed; WEA out; **no further R1-blocking SA.mutate deepen** |
| `docs/architecture/adr/ADR-017_…md` Consequences | “R1 SA.mutate stop line \| **CLOSED** for non-WM deepen track” |

That is an **ADR / stop-line queue** status, not Art VI soak.

### C. Phase “complete” (third meaning)

| Source | Text |
|--------|------|
| `docs/governance/PHASE_COMPLETION_RULE.md` L11–18 | Phase complete only if features+audits+constitution updates on `main`, no active branch holds phase-only code |

### Tom’s unified statement (for both audits)

```text
Closed (performance debt)  := Art XV register Closed per Art VI DoD (incl. soak)
CLOSED (SA.mutate stop line) := ADR-015/016/017 accepted on main; no further R1-blocking
                               mutate ADR required (R1_UNGATED_STOP_LINE.md)
Phase complete             := PHASE_COMPLETION_RULE.md four conditions
```

These are **genuinely different criteria**, not one rule said two ways.  
v2’s phrase “production Closed” for SA was **Tom analogy**, not a cited constitution term — **withdrawn as a formal label**. Prefer: **stop-line CLOSED** (met for ADR queue) vs **hardening incomplete** (F1–F4 open).

---

## Label / score movements (rev 2 → 2.1)

| Item | Before (v2) | After (2.1) | Why |
|------|-------------|-------------|-----|
| Overall score | 74 | **74** (unchanged) | Rubric now shown; math already targeted 74 |
| Architecture Compliance | PASS WITH FINDINGS | **PASS (structural) / FAIL-outcome (F2)** | Q2 |
| “Production Closed” | Informal bar | **Withdrawn as formal term**; use stop-line CLOSED vs hardening incomplete | Q6 |
| Primitive Reuse | N/A | **N/A** (unchanged; not PASS) | Q2 |
| Comparability to PERF 69 | Implied by prose | **Explicit: not comparable** | Q5 |

```
Overall Score: 74
Status: PARTIALLY_IMPLEMENTED
Implementation Maturity: LEVEL_3

Constitution Compliance:     N/A as Art VI/XV Closed-DoD (wrong constitution);
                             PASS for ACC host-layer rules checked in this track
Architecture Compliance:     PASS (structural) / FAIL-outcome (F2 WM type=memory)
Primitive Reuse Compliance:  N/A
CustomTkinter Compliance:    N/A
AppState Compliance:         PASS (bus facts)
GitHub Pattern Compliance:   PASS
Outcome / hardening:         FAIL (F1 unpinned; F2 anti-pinned; F3–F4 unpinned)
Stop-line (ADR queue):       CLOSED per R1_UNGATED_STOP_LINE.md L18–29
```

---

# Follow-up (rev 2.2) — challenge on addendum

## A. Governance follow-up (from Q6) — flag upward

Three local “Closed/complete” definitions remain unreconciled:

| Doc | Local meaning |
|-----|----------------|
| `PERFORMANCE_CONSTITUTION.md` Art VI + XV | Perf debt Closed only after soak DoD |
| `docs/audits/R1_UNGATED_STOP_LINE.md` | ADR/stop-line queue CLOSED |
| `docs/governance/PHASE_COMPLETION_RULE.md` | Phase complete on `main` |

**Recommended org follow-up (not in this audit’s score):** one governance doc that defines **Closed** once (or a typed vocabulary: `debt_closed` / `stop_line_closed` / `phase_complete`), with the others deferring by reference. Until then, audits must **name which Closed** they mean.

## B. PERF 20 vs 23 — resolved

| Collect | Files | Count |
|---------|-------|------:|
| Challenge list (4 files, no metrics) | perf002, coalesce, ui_freeze, runtime_identity | **20** |
| PERF Tom verbatim (`…FREEZE_CLOSEOUT…` ≈L272–278) | + `tests/test_appstate_notify_metrics.py` | **23** |

Gap = exactly the three metrics tests. **PERF’s 23 reproduces.** SA Q3’s first “20” was an incomplete file list, not a PERF arithmetic error. Both suites remain node-id disjoint.

## C. Dimension table — shown and verified

See **Q1 weighted table** above (rev 2.1, with Σ line and expanded arithmetic). That table **is** the recalibrated one (79/81/70/75/72/74/60/74/74/60 → 7400/100=74). It is the same 74 as the deduction rubric, shown two ways — **not** independent corroboration.

## D. F2 status upgrade: anti-pinned + migration gate

F2 is **not** merely unpinned. `tests/test_adr017_sa_mutate_disposition.py:13` green-asserts `create_node ∈ supported`. Live echo writer: `orchestration_service.py:404–431` (`type: memory`). **Do not “fix F2” by deleting `create_node` support** without writer inventory + pin rewrite (Q4).
