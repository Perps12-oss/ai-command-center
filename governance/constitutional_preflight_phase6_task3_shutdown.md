# Phase 6 Task 3 — Async Shutdown Cleanup Constitutional Pre-Flight

## Task Description

Stabilize the async service shutdown path in `ai_command_center/services/ollama_http_service.py` to eliminate noisy pending-task warnings from health checks and connector tasks. The fix is service-internal: wait for the shutdown coroutine to complete before joining the background asyncio thread, and drain the active stream and health tasks before closing the aiohttp session.

Also suppress the expected `ClientConnectionResetError` traceback printed by the Phase 3B mock server when the cancellation test disconnects the client mid-stream; this is test-harness noise, not a behavior change.

## Authorities Reviewed

1. `PROJECT_CONSTITUTION_V4.md` — supreme authority; service lifecycle, no architecture bypasses.
2. `AGENTS.md` — implementation directives for coding agents.
3. `docs/ARCHITECTURE.md` — data flow and service boundaries.
4. `docs/ARCHITECTURE_ENFORCEMENT.md` — service lifecycle rules.
5. `docs/PHASE6.md` — Phase 6 scope and exit criteria.

## Files Reviewed

1. `ai_command_center/services/ollama_http_service.py` — async shutdown path.
2. `ai_command_center/services/base.py` — `BaseService` lifecycle contract.
3. `ai_command_center/core/event_bus.py` — thread-safe EventBus.
4. `scripts/verify_phase3b.py` — mock server used in Phase 3B gate.
5. `tests/test_ollama_http_service.py` or equivalent — existing tests (if any).

## Protected Assets Impacted

- **Service Lifecycle Framework** — `_on_load`/`_on_unload` remain the only lifecycle hooks; no public API changes.
- **EventBus Architecture** — no new topics or subscriptions.
- **OllamaService API v1.0** — unchanged.

## Sources of Truth Impacted

No new source-of-truth authority. The Ollama service loop lifecycle remains owned by `OllamaHttpService`.

## Architectural Invariants Impacted

- **Ownership Flow**: PRESERVED.
- **No Direct Service-to-Service Calls**: PRESERVED.
- **Service Lifecycle**: PRESERVED.

## Contracts Impacted

- `OllamaService API v1.0` — unchanged.
- Chat lifecycle topics — unchanged.
- `ollama.status` — unchanged.

## Gate Impact Assessment

- `python scripts/verify_constitution.py` — must pass.
- `python scripts/verify_contracts.py` — must pass.
- `python scripts/verify_phase3b.py` — must continue to pass (uses `OllamaHttpService`).
- `python -m unittest discover -s tests -v` — must pass; may add a regression test for clean shutdown.

## Historical Gate Impact

No historical gates removed, bypassed, or weakened.

## Regression Risk

**Risk Level: LOW**

Reasoning:
- Change is confined to service shutdown ordering.
- No public API or contract changes.
- Existing `OllamaServiceBase` contract and behavior are preserved.
- All existing gates continue to pass.

Mitigation:
- Run `verify_phase3b.py` and full unit test suite after implementation.
- Add a targeted unit test that loads and unloads `OllamaHttpService` without raising unhandled exceptions or warnings.

## Constitutional Status

**APPROVED**

Implementation may proceed.
