# PERFORMANCE_CONSTITUTION.md

## Version: 1.0

## Status: Peer Constitution — Runtime Quality

## Classification: Performance Engineering Governance

---

# PREAMBLE

This constitution governs **runtime quality and performance engineering** for AI Command Center (ACC).

It is a **peer** to `PROJECT_CONSTITUTION_V4.md`:

- `PROJECT_CONSTITUTION_V4.md` remains the supreme authority for architecture and governance.
- This document is the authority for performance budgets, investigation discipline, and Program 1 (Runtime) quality gates.
- **Conflict rule:** If there is a conflict, **V4 wins**, unless V4 is explicitly amended.

Mission: separate **runtime stability** from **intelligence**. Program 1 moves data reliably. It does not implement cognition.

**Assume the current architecture is correct until evidence proves otherwise.**

**Prefer repairing existing systems over introducing new ones.**

**The burden of proof is on replacing code, not on keeping it.**

---

# ARTICLE I — EVIDENCE-DRIVEN PERFORMANCE

Performance work must be evidence-driven.

No optimization may be implemented unless:

1. A measurable bottleneck exists.
2. The bottleneck has been reproduced.
3. The proposed fix targets that bottleneck specifically.
4. Success criteria are defined before implementation.
5. Before/after measurements are recorded.

Avoid speculative optimization.

---

# ARTICLE II — PROGRAM OVERLAY

Do **not** rename existing repository programs or phases.

Conceptual overlay only:

| Concept | Maps to |
|---|---|
| Program 1 — Runtime Platform | Stabilization / runtime spine work |
| Program 2 — Brain (Cognition) | Brain architecture & contracts |
| Program 3 — Workspace UX | UI render-only surfaces |

**Program fence**

Do not propose changes outside Program 1.

If investigation discovers another Program is involved, **stop and request approval**.

Current objective: Program 1 (Runtime Stabilization). Program 2 data contracts only when explicitly requested.

---

# ARTICLE III — PERFORMANCE GATES

Measurable gates (release intent):

| Gate | Target |
|---|---|
| UI thread | Avg &lt;2 ms, P99 &lt;8 ms |
| EventBus sync handlers | &lt;5 ms |
| Navigation (view switch) | &lt;16 ms |
| SQLite / disk / LLM on UI thread | **Forbidden** (must be async / off-thread) |
| AppState | Dirty updates only; no full rebuilds |

---

# ARTICLE IV — PERFORMANCE BUDGETS

Every subsystem has hard targets. “Make it faster” is not a requirement; meeting the budget is.

### EventBus

| Metric | Budget |
|---|---|
| Publish | &lt;0.2 ms |
| Dispatch (sync handler) | &lt;5 ms |
| Queue depth | &lt;100 |

### AppState

| Metric | Budget |
|---|---|
| Reducer | &lt;0.5 ms |
| Notify | &lt;1 ms |
| UI Apply | &lt;2 ms |

### Navigation

| Metric | Budget |
|---|---|
| View switch | &lt;16 ms |

### Inspectors

| Metric | Budget |
|---|---|
| Refresh | &lt;5 ms |

### Telemetry

| Metric | Budget |
|---|---|
| Insert | **async** |

### SQLite

| Rule | Budget |
|---|---|
| UI thread | **Never** |

---

# ARTICLE V — MEASUREMENT SPLIT

**CI proves correctness. Local proves responsiveness.**

### CI (mandatory)

- Headless benchmarks
- Unit tests
- Synthetic performance tests (e.g. `tests/test_perf_architecture.py`, reducer/soak tests)

### Local / release gate (Windows ARM64)

- Real GUI
- Soak tests
- Performance Inspector (`Ctrl+Shift+P`)
- `ACC_UI_RUNTIME freeze_fix=v5` (or current fingerprint)

Headless Linux cannot claim UI-thread or Tk layout budgets.

---

# ARTICLE VI — WORKING RULES

Every optimization follows:

```text
Measure → Root cause → Smallest fix → Implement → Benchmark → Soak test
```

Every significant architectural decision must be recorded as an ADR (Context, Decision, Alternatives, Consequences, Rollback).

**Definition of Done** for every performance task:

- Tests pass
- Benchmarks pass
- Soak test passes
- No regression
- Telemetry updated
- Documentation / ADR updated

Engineering philosophy:

- Prefer deletion over addition.
- Prefer simplification over abstraction.
- Prefer immutable data over mutable state.
- Prefer measurement over intuition.
- Prefer deterministic behavior.
- Prefer explicit contracts over implicit coupling.

The objective is not to build more software. It is to reduce complexity while increasing capability.

---

# ARTICLE VII — PERFORMANCE INVESTIGATION PROTOCOL

Before **any** implementation, produce this report:

```text
# Performance Investigation Report

Problem
--------
What user-visible symptom exists?

Evidence
--------
What profiling, telemetry, traces or logs prove it?

Call Chain
----------
Exactly which call path causes it?

Ownership
---------
Which Program owns the issue?

Program 1
Program 2
Program 3

Root Cause
----------
Single most likely cause.

Alternative Causes
------------------
List competing hypotheses.

Chosen Fix
----------
Smallest change that addresses root cause.

Why this fix?
-------------
Why this instead of alternatives?

Blast Radius
------------
Exactly which files/services change?

Success Criteria
----------------
How will we measure improvement?

Rollback
---------
How do we revert?
```

No runtime patches before approval of this report.

Draft PRs are allowed **only after** approval.

---

# ARTICLE VIII — OPTIMIZATION LADDER

Every optimization must climb this ladder in order. Do not jump to threading or micro-optimization.

```text
Delete unnecessary work
        ↓
Avoid duplicate work
        ↓
Coalesce work
        ↓
Cache work
        ↓
Move work off UI thread
        ↓
Optimize algorithm
        ↓
Optimize data structure
        ↓
Parallelize
        ↓
Micro-optimize
```

---

# ARTICLE IX — SEVERITY LEVELS

| Level | Meaning |
|---|---|
| **S0** | UI freeze, App Not Responding, deadlock, infinite recursion |
| **S1** | Multi-second stall |
| **S2** | Visible jank, dropped frames |
| **S3** | Performance debt |

Prioritize by severity. Do not spend S3 effort while S0/S1 remain open without explicit approval.

---

# ARTICLE X — ANTI-PATTERNS (FORBIDDEN)

Forbidden:

- Blocking SQLite on UI thread
- Blocking network on UI thread
- Blocking filesystem on UI thread
- Calling LLM synchronously (on UI / sync publish path)
- Large AppState rebuilds
- Recursive EventBus publishes
- Full inspector rebuilds
- Global locks around UI work
- Background threads touching Tkinter
- Multiple publishes for identical state
- Repeated layout rebuilds
- Long sync EventBus handlers
- Speculative optimizations
- Massive refactors
- Redesigning architecture “to help”
- Renaming services / introducing frameworks / moving files without necessity
- Combining unrelated fixes
- Cleanup unrelated to the task
- Enabling EventBus async flags by default without explicit approval
- Changing which topics are `SYNC_CRITICAL` during initial stabilization (reduce work inside handlers only)

---

# ARTICLE XI — RUNTIME OWNERSHIP

| Component | Owner |
|---|---|
| EventBus | Runtime (Program 1) |
| AppState | Runtime (Program 1) |
| SQLite | Runtime (Program 1) |
| Telemetry | Runtime (Program 1) |
| UIQueue | Runtime (Program 1) |
| Execution Authority / scheduling | Runtime (Program 1) |
| World Model | Brain (Program 2) |
| Situation Engine | Brain (Program 2) |
| Decision Engine | Brain (Program 2) |
| Planner | Brain (Program 2) |
| Learning | Brain (Program 2) |
| Tk Views | UI (Program 3) |

Brain and UI must not become the system of record for runtime scheduling, EventBus policy, or SQLite ownership.

---

# ARTICLE XII — ESCALATION RULES

If a task touches any of:

- EventBus
- Execution Authority
- Threading
- SQLite
- AppState
- UI Dispatch
- Scheduling

it must:

1. Produce analysis
2. Identify affected systems
3. Estimate blast radius
4. **Wait for approval**

before implementation.

Approval authority: project owner (human). Analysis-only work may proceed; draft PRs only after approval.

---

# ARTICLE XIII — PROGRAM 1 INVESTIGATION ORDER

1. AppState notification storms
2. Inspector rebuilds
3. Navigation
4. SQLite contention
5. SYNC_CRITICAL handler *work* reduction (topic classification out of bounds until later approval)

One bottleneck per implementation PR. Measure before and after. Merge. Repeat.

Tool-executor sync `communicate` is a **Non-Goal** for the first pass unless profiling proves freeze contribution.

---

# ARTICLE XIV — NON-GOALS

Do not:

- Redesign architecture
- Rename services
- Introduce frameworks
- Move files unless necessary
- Optimize speculative bottlenecks
- Combine unrelated fixes
- Perform cleanup unrelated to the task
- Drift into Program 2 (Brain) or Program 3 redesign during Program 1 work

---

# ARTICLE XV — PERFORMANCE DEBT REGISTER

Every performance issue remains tracked until closed.

Living register (update when items open/close; IDs are stable):

| ID | Issue | Severity | Owner | Status | Baseline | Target |
|---|---|---|---|---|---|---|
| PERF-001 | AppState notification storms | S1 | Runtime | Open | UI notify rate unmeasured headless; hot reduces: chat.chunk / service.* / system.snapshot @ tip `5cef96b` | Instrument then &lt;25 UI notifies/s under soak |
| PERF-002 | Inspector rebuilds | S2 | Runtime | Open | N/A headless | &lt;5 ms refresh |
| PERF-003 | `settings.snapshot` handler over budget | S1 | Runtime | Open | max 82 ms (`OpenAIHttpService`) | &lt;5 ms |
| PERF-004 | Navigation Tk `_show_view` cost | S2 | Runtime | Open | N/A headless | &lt;16 ms view switch |
| PERF-005 | SQLite lock contention under workers | S2 | Runtime | Open | write max ~7.7 ms microbench; WAL on | No UI-thread wait; retain async telemetry |

Source baseline: `docs/audits/PERF_BASELINE_REPORT_2026-07-26.md`.

---

# ARTICLE XVI — RELATED DOCUMENTS

| Document | Role |
|---|---|
| `PROJECT_CONSTITUTION_V4.md` | Supreme architecture / governance |
| `docs/UI_CONSTITUTION.md` | UI governance |
| `docs/architecture/ASYNC_EVENTBUS_POLICY.md` | Sync/async dispatch policy |
| `docs/audits/PERFORMANCE_RCA_UI_FREEZE_2026-07-24.md` | Freeze RCA |
| `docs/audits/PERF_ARCHITECTURE_EVIDENCE_2026-07-24.md` | Post-fix evidence |
| `docs/audits/PERF_BASELINE_REPORT_2026-07-26.md` | Phase 0 before snapshot |
| `docs/architecture/adr/ADR-007_APPSTATE_NOTIFICATION_STORMS.md` | First investigation ADR |
| `ai_command_center/core/perf/metrics.py` | `PerfMetrics` |

---

# END OF PERFORMANCE CONSTITUTION
