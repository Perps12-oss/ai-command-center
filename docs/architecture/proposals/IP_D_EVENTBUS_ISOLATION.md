# IP-D — EventBus measurement and isolation

**Status:** GATE 2 CLOSED 2026-08-14 — DEFER WITH CONDITION (see §11 below). No ADR issued yet.  
**Stream:** D  
**Parent ADR:** none for multi-pool isolation. R4b single-queue is **live**.  
**Verification authority:** [`PERFORMANCE_CONSTITUTION.md`](../../../PERFORMANCE_CONSTITUTION.md)  
**Baseline:** [STRATEGIC_GAP_MATRIX.md](../../audits/STRATEGIC_GAP_MATRIX.md) Stream D

---

1. **Problem.** Possible UI starvation / cross-topic interference on a single dispatch worker. Isolation must be justified by **measurement**, not enthusiasm.

2. **Exists.** `async_dispatch=True` single `event-dispatch` queue; SYNC_CRITICAL vs ASYNC_ELIGIBLE policy; queue depth / drop / handler duration / topic counts; backpressure (telemetry drop, critical inline). No `tiered_dispatch_policy.py` on main. Abandoned branch is not a merge candidate.

3. **Owning boundary.** `EventBus` + dispatch policy module. UI remains a renderer on UIQueue. PERFORMANCE_CONSTITUTION budgets verify; they do not authorize pools by themselves.

4. **Remain authoritative.** Single-queue FIFO **until** a new Accepted ADR says otherwise. SYNC_CRITICAL ordering for settings/UI_COMMAND/EA decision. Art. XVII UIQueue event-driven (no ≤100 ms polling).

5. **New behavior.** **Stage 1 (required first):** instrument and load-test queue depth, dispatch latency, handler duration, contention, burst, UI impact (Windows ARM64 for GUI budgets), worker starvation, cross-topic interference. Produce Performance Investigation Report. **Stage 2:** smallest justified isolation (possible UI/critical vs runtime vs background) **only if** Stage 1 + Gate 2 ACCEPT.

6. **Rejected.** Merging `cursor/phase5-async-eventbus-744e`; hard-coding three pools before data; dropping events other than allowed telemetry policy without ADR.

7. **Dependencies.** Existing R4b; PERF Art V (CI vs local GUI); Streams A–C add bus load — measure after their emission patterns are known or include them in the harness.

8. **Invariants.** Art. VII zero regression; Art. XII (performance as verified requirement); no UI work on bus thread beyond budgets.

9. **Tests.** Load tests: no UI starvation (where measurable); no priority inversion; bounded queues; isolation if accepted; predictable shutdown; ordering where required.

10. **Invalid if.** Pools ship without investigation report; isolation tests break required FIFO without ADR; GUI budgets claimed from Linux headless.

**Gate 2 ask:** DEFER WITH CONDITION = “Stage 1 report required; isolation ADR number reserved.” ACCEPT isolation topology only after the report. REJECT isolation if measurement shows R4b meets budgets.

---

## 11. Gate 2 Decision — Wave 1 Closure (2026-08-14)

**Decision:** **DEFER WITH EXPLICIT CONDITION.** This is the one Wave-1 stream that closes Gate 2 without an ACCEPT or a new ADR, per the program's own rule that isolation must be justified by measurement, not enthusiasm.

**Condition to reopen Gate 2:** A completed **Stage 1 Performance Investigation Report** — instrumented, load-tested evidence of queue depth, dispatch latency, handler duration, contention, burst behavior, worker starvation, and cross-topic interference under realistic load, gathered on Windows ARM64 for any GUI-impact claim (per PERF Art. V — Linux headless CI does not substitute for GUI budget evidence). Streams A–C add bus load once their emission patterns land; include that load in the harness or explicitly note it's measured separately.

**Until that report exists and is reviewed:**
- Single-queue FIFO (R4b) remains authoritative and unchanged.
- No `tiered_dispatch_policy.py`, multi-pool dispatch, or any isolation code lands on `main`.
- The abandoned branch `cursor/phase5-async-eventbus-744e` remains **not a merge candidate** regardless of any other pressure to revive it.

**ADR numbering:** No ADR is issued now. This program's Wave 1 closure assigns ADR-024 to Stream E and ADR-025 to Stream F (see `docs/architecture/adr/README.md`); Stream D's isolation ADR, if the Stage 1 report justifies one, takes the next free number at that time (currently **ADR-026**, but re-check the ADR README before drafting since other streams may claim numbers first).

**This is not a stall.** Stage 1 (instrumentation + load testing) is itself authorized, unblocked work — it requires no architecture decision, only measurement. It may start immediately; only Stage 2 (any actual isolation topology) remains gated on this DEFER.
