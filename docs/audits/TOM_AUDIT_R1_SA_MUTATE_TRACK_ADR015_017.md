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
