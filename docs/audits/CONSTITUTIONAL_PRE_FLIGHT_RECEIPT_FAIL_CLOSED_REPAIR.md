# Constitutional Pre-Flight — Receipt Fail-Closed Repair (B-1)

**Status:** PRE-FLIGHT (before implementation)  
**Baseline tip:** `9fca028` (PR #166 / Phase A+B)  
**Branch:** `cursor/receipt-boundary-fail-closed-323d`  
**Owner decision:** implement repair plan; prefer existing sync mechanism over a new EventBus topic if possible.

---

## 1. Authority read

| Level | Bearing |
|-------|---------|
| V4 | No amendment. Strengthens an existing gate (Art. VI not engaged as removal). |
| ADR-006 / ADR-018 | Untouched. EA intake and sole `TOOL_INVOKE` publisher unchanged. |
| O-1 | No EventBus tier changes. |
| R1_UNGATED_STOP_LINE | Untouched. |

---

## 2. Necessity proof — is `RECEIPT_REQUEST` required?

| Option | Verdict |
|--------|---------|
| New `execution.run.receipt_request` topic | **Rejected as unnecessary.** Works, but adds an EventBus contract solely to ask OrchestrationService for evidence EOS can obtain synchronously. |
| Direct EOS → OrchestrationService method call | **Rejected.** Violates Rule 3 (no service-to-service calls). |
| Keep COMPLETE-then-FAILED | **Rejected.** Violates the invariant (goal COMPLETE commits first). |
| **Shared sync emit of existing `ORCHESTRATION_RECEIPT`** | **Chosen.** Factor receipt+truth publish into `orchestration/receipts/` (Inv 11 single module). EOS calls it **before** `EXECUTION_RUN_COMPLETE`. Uses the existing receipt topic; no new bus contract. |

**Conclusion:** A new RECEIPT_REQUEST topic is **not** the smallest safe way. Existing synchronous `EventBus.publish(ORCHESTRATION_RECEIPT)` (inline `SYNC_STANDARD`) already establishes ledger evidence before any subsequent publish returns.

---

## 3. Invariant

```text
NO RECEIPT → NO EXECUTION_RUN_COMPLETE → NO GoalStatus.COMPLETE
           → terminal EXECUTION_RUN_FAILED only
```

---

## 4. Scope

- B-1 fail-closed repair (EOS + shared receipt emit + OrchestrationService dedupe on success path)
- Invariant regression tests
- CI A2 timeline SQLite lock (genuine Phase-A race); no test weakening
- N-2/N-1/N-3/F-* not expanded except N-2 only if required for CI (lock is sufficient)

---

## 5. Non-goals

Phase C fossils, B5, EventBus tier changes, new services, ADR text edits.
