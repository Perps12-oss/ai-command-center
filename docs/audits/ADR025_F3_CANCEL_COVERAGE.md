# ADR-025 F3 — Cancel coverage verify (Wave 4 Gate 4)

**Date:** 2026-08-17  
**Authority:** ADR-025 §9 F3  
**Tree:** Gate 4 Adapt implementation branch

## Inventory

| Surface | Coverage before Gate 4 | Verdict |
|---------|------------------------|---------|
| Chat / LLM cancel (`UI_CHAT_CANCEL` → `CHAT_CANCELLED` / `LLM_CANCEL`) | `ollama_service.py`, `openai_http_service.py` subscribe and cancel streams | **Covered** |
| Agent cancel (`AGENT_CANCEL_REQUEST`) | UI publishes; AgentRuntimeService subscriber path | **Covered** |
| Goal cancel (`GOAL_CANCEL_REQUEST` / `GOAL_CANCELLED`) | UI publishes; scheduler owns fact | **Covered** |
| Orchestration `run_id` cancel | No topic / no handler on `ExecutionOrchestratorService` | **Gap** |
| Creation lock (same `run_id`) | `_on_run_request` overwrote `_runs[run_id]` | **Gap** |

## Fill (this Gate 4)

- New topic `execution.run.cancel` (`EXECUTION_RUN_CANCEL`) — LLM/agent/goal cancel cannot target orchestrator runs.
- Orchestrator subscribes and `_fail_run`s the active run.
- Duplicate `EXECUTION_RUN_REQUEST` with an active `run_id` publishes `EXECUTION_RUN_FAILED` with `run already active` without replacing the live run.

Tests: `tests/test_orchestrator_run_cancel.py`.
