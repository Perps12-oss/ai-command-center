# IP-D — EventBus measurement and isolation

**Status:** GATE 1 DRAFT — awaiting owner Gate 2  
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
