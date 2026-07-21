# PHASE 0R — Repository Truth Reconciliation

> **Superseded by [`PHASE_R1_RUNTIME_RECONCILIATION.md`](PHASE_R1_RUNTIME_RECONCILIATION.md)** — same goal (make `main` truthful), with strict priority order and runtime authority decision gate.  
> Keep this file as historical pointer only.

**Status:** SUPERSEDED → see PHASE R1  
**Date:** 2026-07-20

---

## Why this exists

Two audits looked contradictory. They were not.

| Layer | Finding |
|-------|---------|
| UI / inventory (Devin branch confusion vs Canon) | Surfaces and packages on `main` are further along than stale branches suggested |
| Runtime / completion (Cursor code verification) | Many plans marked COMPLETE were ahead of the **wired** system |

Combined state:

```text
Documentation claims  ──ahead of──►  UI surfaces  ──ahead of──►  Runtime authority paths
```

Control room exists. Several systems behind the glass are incomplete or bypassed.

**Do not continue Phase B UI expansion until 0R exit criteria pass.**

---

## Goal

**Make `origin/main` truthful.**

Bring docs, UI inventory, and runtime composition into the same reality so later phases plan against the executable system—not a paper architecture.

---

## Non-goals

- New Mission Control workspaces / Phase B chrome  
- Rewriting Phase 8–10 feature scope  
- Declaring phases COMPLETE without Exists+Wired+Tested evidence  

---

## Definition: Exists vs Wired vs Tested

| Column | Meaning | Evidence |
|--------|---------|----------|
| **Exists** | Module/class present on `main` | path + symbol |
| **Wired** | Constructed/registered in composition root and reachable from product startup / command path | `service_factory.py`, `application.py`, `create_application` + `startup` |
| **Tested** | Automated tests cover the **wired** path (or honest unit-only note) | `tests/` + whether factory path is exercised |
| **Status** | `MISSING` / `PARTIAL` / `WIRED` / `AUTHORITATIVE` | see matrix rules |

### Status rules

| Status | Rule |
|--------|------|
| MISSING | Exists = no |
| PARTIAL | Exists = yes; Wired = no **or** Tested = unit-only while product bypasses |
| WIRED | Exists + Wired; tests may still be thin |
| AUTHORITATIVE | Exists + Wired + end-to-end/integration proof that the intended path is the live path |

**Forbidden PASS:** “`Foo.py` exists” alone.

---

## Workstreams

### 0R.1 — Runtime authority audit

Trace every operator-facing action:

```text
UI intent → EventBus → service_factory wiring → authority services → execution → receipt → verification
```

Deliverable: `docs/audits/RUNTIME_AUTHORITY_AUDIT.md`  
Questions:

1. Does every action flow through the intended architecture?  
2. Where does composition bypass planned kernels (e.g. `OperatorKernel`)?  
3. Which “old services” remain the live path?

### 0R.2 — Implementation Truth Matrix

Maintain `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md` (seeded with this milestone).

For each capability:

```text
Capability:
- exists ✅/❌
- imported by runtime ✅/❌
- used by execution/command path ✅/❌
- tested end-to-end ✅/❌
```

### 0R.3 — Doc / plan alignment

Already started:

- Canon inventory SoT  
- DOC_HYGIENE (archive requires `main` code proof)  
- Phase plans reclassified PARTIAL / SUPERSEDED / STALE  

Remaining under 0R:

- No plan may say COMPLETE without AUTHORITATIVE matrix row  
- Master roadmap status tables reconciled to matrix  
- Stale branches/PRs closed (`phase-11a-command-center` / PR #75)

### 0R.4 — Gap backlog for Devin (wiring only)

Ordered by authority risk (not UI polish):

1. OperatorKernel — exists, **not wired** (classic paper architecture)  
2. AgentCoordinator / PlanningEngine — test-only construction  
3. Predictive engine / UndoReplay — packages exist, **not in factory**  
4. Cross-platform hotkey/tray — stubs on live getters  
5. Phase 5/6 remaining exit criteria (async pools / MCP scan) as matrix rows  

Devin implements only after Guardian marks a row as the active gap.

---

## Exit criteria (0R complete)

0R may be declared complete on `main` only when:

1. [ ] Runtime authority audit published and reviewed  
2. [ ] Truth matrix covers OperatorKernel, GoalEngine, AgentCoordinator, PlanningEngine, ExternalCapabilityBridge, WorldModel/Brain, Predictive, UndoReplay, Graph (`BaseGraphCanvas`), Timeline, Inspector, ExecutionAuthority, StateAuthority, cross-platform hotkey  
3. [ ] Every ACTIVE plan in `docs/plans/` header status matches matrix (no false COMPLETE)  
4. [ ] Superseded branches that caused inventory confusion are closed/deleted  
5. [ ] Tom audit of 0R: **PASS** or **PASS WITH CONDITIONS** with no “exists ≠ wired” CRITICAL open  

Phase B UI and Phase 8–10 **feature** work stay blocked until then. Wiring fixes that close matrix rows are in scope for 0R.

---

## Relationship to other phases

```text
PHASE 0R (truth + wiring alignment)
    │
    ├── unblocks honest Phase 8–10 planning
    └── unblocks Phase B UI evolution (after UI primitives already on main are treated as evolve-not-rewrite)
```

Frontend Phase 11 surfaces on `main` are **inventory**, not proof of runtime completeness.

---

## References

| Doc | Role |
|-----|------|
| `docs/audits/REPOSITORY_TRUTH_CANON.md` | What UI assets exist on `main` |
| `docs/audits/PHASE_PLANS_ARCHIVE_VERIFICATION.md` | Plan exit criteria vs code |
| `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md` | Exists / Wired / Tested |
| `docs/governance/DOC_HYGIENE.md` | Archive gate |
