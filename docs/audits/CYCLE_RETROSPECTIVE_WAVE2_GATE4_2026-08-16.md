# Cycle retrospective — Wave 2/3 Gate 4 (2026-08-16)

**Tip at close of this cycle’s merges:** `origin/main` included Gate 4 streams A, B, C, E-M1, B5 (merge commits through `f35cb98` / PR #193).  
**This document:** pause, what worked, what to do next. Not a phase-complete declaration.

## What shipped

Gate 4 **implementation** against Gate 3 plans:

- Explainability (A), autonomy bands (B), model M3/M4 (C), read-only federation (E), Hero EA intake verification (B5).
- Followed **ADR topics and modules**, not the informal delegation’s invented EventBus names (`DECISION_RECORD_CREATED`, `CONFIDENCE_ESCALATION_REQUIRED`, etc.).
- Stream B stacked on A (shared `_publish_decision_and_autonomy`).

## What we refused

- EventBus multi-pool revival.  
- Vector/embedding federation.  
- Capability-registry model pooling / complexity orchestration (ADR-023 out of scope).  
- Restoring OperatorKernel / Predictive / Undo.

## What measurement showed (same cycle, Stage 1)

See [`EVENTBUS_STAGE1_CONTENTION_REPORT.md`](EVENTBUS_STAGE1_CONTENTION_REPORT.md).

**Isolation stays locked.** SYNC_CRITICAL was not starved. Burst queue depth exceeded the paper &lt;100 target on an unbounded queue; that is not UI starvation and is not an ADR.

## Friction

- GitHub PR #192 stayed OPEN after a local merge to `main` until humans merged/closed it. Prefer GitHub merge when `gh` write is available.  
- Five parallel streams needed explicit “follow the ADR, not the brief.”  
- UI Gate 5 cannot close in this Cloud environment.

## Next wave (Queue 1 order)

| Order | Work | Gate |
|-------|------|------|
| 1 | **Gate 5 verification** for A/B/C/E-M1/B5 — [`GATE5_VERIFICATION_SCOPE.md`](GATE5_VERIFICATION_SCOPE.md). Tests/governance here; GUI on Windows ARM64. | 5 |
| 2 | **Gate 6 close-out** per stream only after Gate 5 evidence is on `main` (docs agree with code). | 6 |
| 3 | Stream D Stage 2 **only if** a later report meets the unlock conditions. Otherwise leave R4b. | D Gate 2 reopen |
| 4 | Stream E vectors — still DEFER; needs a future proposal + UCGS profile. | not opened |
| 5 | Stream F Adapt rows — Wave 4, each with its own Gate 3 plan (ADR-025). | Wave 4 |
| 6 | Wave 5 full-system path, then Stream G Cross-OS. | Waves 5–6 |

No extra tickets from historical `docs/plans/` phase files. No deployment program unless the owner adds it to Queue 1.

## Honest status

| Item | Status |
|------|--------|
| Wave 1 architecture closure | Closed on `main` |
| Gate 4 product code (named streams) | On `main` |
| Gate 5 | **Scoped, not complete** |
| Stream D isolation | **Blocked** (Stage 1 report does not unlock) |
| Cross-OS | Still the only remaining **strategic** gate, not opened |
