# Change Note — Receipt Fail-Closed Repair (B-1) + Timeline Lock

**Branch:** `cursor/receipt-boundary-fail-closed-323d`  
**Base tip before repair:** `9fca028` (PR #166)  
**Pre-flight:** `docs/audits/CONSTITUTIONAL_PRE_FLIGHT_RECEIPT_FAIL_CLOSED_REPAIR.md`

---

## Necessity proof (owner constraint)

A new `RECEIPT_REQUEST` EventBus topic was **not** required.

Receipt evidence is established by synchronously publishing the **existing**
`ORCHESTRATION_RECEIPT` topic (default `SYNC_STANDARD`, inline handlers) via a
shared helper in `orchestration/receipts/boundary_emit.py` **before**
`EXECUTION_RUN_COMPLETE`. That is a smaller surface than a new bus contract.

---

## Behaviour

`ExecutionOrchestratorService._complete_run`:

1. Clear stale ledger ids  
2. `emit_execution_receipt(...)` → `ORCHESTRATION_RECEIPT` + truth  
3. If receipted → **only** `EXECUTION_RUN_COMPLETE` (with `receipt_already_emitted`)  
4. Else → **only** `EXECUTION_RUN_FAILED(receipt_boundary_violation=True)`  

Never COMPLETE-then-FAILED.

`OrchestrationService` reuses the same emit helper; on success COMPLETE with
pre-emitted receipt it performs fanout only (no duplicate receipt).

## CI

`TimelineRepository` uses `connection_lock` so Phase-A async `TOOL_INVOKE`
cannot race timeline writes on the shared SQLite connection (ubuntu py3.11 failure).

Follow-up babysit harden (same failure mode after tip `58757f6`):

- `WorkspaceOsService._on_launch_resource` records the launch timeline event
  **before** publishing `WORKFLOW_EXECUTION_REQUEST` (app `EventBus` uses
  `async_dispatch=True`, so `TOOL_INVOKE` is worker-threaded).
- `ExecutionRunRepository` / `ExecutionEventRepository` also take
  `connection_lock` — they are the concurrent writers on the async path that
  previously bypassed the timeline lock.
## Out of scope

N-1, N-3, F-1–F-4, Phase C, B5. N-2 (outcome-gated launch timeline) still deferred.
