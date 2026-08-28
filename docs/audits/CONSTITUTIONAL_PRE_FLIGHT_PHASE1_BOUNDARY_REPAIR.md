# Constitutional Pre-Flight — Phase 1 Boundary Repair

**Date:** 2026-08-27
**Branch:** `devin/1787872864-phase1-boundary-repair`
**Authority:** `PROJECT_CONSTITUTION_V4.md`; `AGENTS.md`; `docs/ARCHITECTURE_ENFORCEMENT.md`;
`docs/ARCHITECTURE.md`; ADR-018 (`tool.invoke` sole publisher); Inv 6 (ContextManager),
Inv 11 (single source of truth), Inv 12 (non-circumvention), Inv 13 (host platform supremacy)
**Source finding set:** adversarial defect audit (2026-08-27), causal clusters 1–3

## Scope

Repair the three confirmed root defects where non-authoritative state could become
authoritative, plus their two direct companions. No new architecture, no wholesale refactor
of EventBus, orchestration, `TruthBoundary`, provider stack, or security policy.

| Item | Defect | Change surface |
|------|--------|----------------|
| P1-A | Provider unavailable was published as `capability.complete`, producing a successful LLM step, a success receipt and `truth_valid=True` for system-generated fallback prose | `services/chat_handler_service.py` |
| P1-B | Provider readiness was non-replayable shadow state: a coalesced status publish or a handler restart wedged a healthy provider as unavailable | `core/events/topics.py`, `services/ollama_http_service.py`, `services/openai_http_service.py`, `services/chat_handler_service.py` |
| P1-C | Workspace bootstrap had only a success transition; a failed/timed-out bootstrap latched and later replayed deferred commands into an unrelated workspace | `services/workspace_bootstrap_service.py`, `core/workspace_os_service.py`, `core/entity/entity_bus_handlers.py` |
| P1-D | Teardown could report incomplete EventBus shutdown and then block forever in `GuardedConnection.close()`; async outcome topics were dropped while receipts were still delivered | `core/event_bus.py`, `core/events/dispatch_policy.py`, `db/conn_sync.py`, `application.py` |
| P1-E | One orchestrated response was persisted twice as an `assistant` message, double-weighting it in later LLM context | `services/orchestration_service.py` |

## Ownership boundaries preserved

- **Provider health stays provider-owned.** `ChatHandlerService._provider_health` remains a
  local *projection*; on a cache miss it publishes `provider.status.query` and the owning
  provider service re-announces its own last known status. Unknown never means healthy.
  No second authoritative health store is introduced (Inv 11).
- **UI remains a renderer/publisher.** Bootstrap correlation travels as event payload fields
  (`bootstrap_id`), not as UI-held business state.
- **Repositories still own persistence.** P1-E removes a duplicate *publisher*, leaving the
  existing `chat.complete` → `SessionService` path as the single assistant-persistence route.
- **No service→service calls added**; every new interaction is an EventBus topic.
- **`TruthBoundary` and `_complete_step()` are untouched** — P1-A is fixed at the producer
  boundary, so no validation logic is weakened (Inv 12: no bypass introduced).
- **Approval / sandbox / allowlists untouched.**

## New contract surface

| Topic | Direction | Payload |
|-------|-----------|---------|
| `provider.status.query` | consumer → provider owner | `provider` (may be empty = all), `requested_by` |
| `ollama.status` / `openai.status` | owner → consumers | existing fields plus `reannounced: true` on a replay |
| `workspace.create.request` / `workspace.create.result` | existing | optional `bootstrap_id` correlation echo |

`capability.error` is an existing topic; P1-A only changes which branch publishes it.

## Lifecycle invariant (P1-D)

```text
EventBus fully stopped  →  no DB-owning work remains  →  DB closes  →  application exits
```

`EventBus.shutdown()` now returns whether dispatch actually stopped; `ApplicationCore.shutdown()`
raises `ShutdownIncompleteError` instead of closing the database under a live dispatch thread.
`GuardedConnection.close(timeout=...)` is bounded: it retries after a best-effort `interrupt()`
and then raises `ConnectionCloseTimeout`, deliberately leaving the handle open rather than
force-closing another thread's open transaction.

## Regression coverage (failure reproduced first)

`tests/test_phase1_boundary_repair.py`

- unavailable provider → `capability.error`, no `capability.complete`, `success=False` receipt,
  `truth_validated=False`, explanation still delivered to the user;
- provider owner re-announces on query, and never invents a status it does not have;
- a restarted `ChatHandlerService` still reaches a healthy provider;
- outcome topics are delivered inline after shutdown starts while chunk topics are dropped;
- `close()` with a foreign open transaction returns bounded instead of hanging;
- one orchestrated response → exactly one persisted `assistant` row.

`tests/test_workspace_bootstrap_service.py`

- correlated success replays only that bootstrap's deferred commands;
- creation failure and timeout clear the latch and report `app.error`;
- an unrelated `workspace.active` does not replay stale commands;
- the deferred queue is bounded.

## Explicitly out of scope

B5 (request identity continuity beyond bootstrap correlation), B6 (nested sync dispatch budget),
B7 (path-constrained read tools), B8 (ShellProvider command policy), duplicate-command
idempotency, B9 (settings diagnostics), B14 (persisted run snapshot completeness).

## Verification

```bash
python3 scripts/verify_constitution.py
python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json
python3 -m ruff check ai_command_center
python3 tools/ucgs_runner.py > .ucgs_last.yaml
python3 tools/ucgs_ci_gate.py .ucgs_last.yaml
APPDATA=/tmp/aicc_appdata python3 -m pytest -m "not slow"
```
