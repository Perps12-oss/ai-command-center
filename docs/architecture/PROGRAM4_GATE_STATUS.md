# Program 4 Gate Status

**Status:** **READY** — Program 3 **COMPLETE**; Program 1 S1–S6 **COMPLETE**; Program 4 slice 2 landed.

**Last assessed:** 2026-07-06 (`feat/program4-slice3-hotkey-workflows-uiqueue`)

Program 4 may not expand platform capabilities until:

1. ~~Program 1 stabilization gates pass~~ — **satisfied** (S1–S6; see evidence below).
2. Program 2 local/CI enforcement remains active (CI block on; local warn).
3. ~~Program 3 workspace adoption~~ — **satisfied** (WII ≥60%, adoption score ~7.0; `tests/test_program3_exit_gate.py`).

---

## Post-Program 3 backlog (2026-07-06)

| ID | Item | Status | Evidence |
|----|------|--------|----------|
| **S1** | Execution reliability | **Done** | `TOOL_INVOKE` async dispatch; `cancel_active_shell` on unload; `tests/test_lifecycle_shutdown.py`, `tests/test_prompt_injection_sandbox.py` |
| **S2** | Shell & tool hardening | **Done** | `CommandSandbox` in `ToolExecutorService` + `workspace_os_actions`; `PermissionService` gate; `shell=False` only |
| **S3** | Provider registry dispatch | **Done** | `service_factory.py` injects `ProviderRegistry` into `ModelRouterService`; `OllamaHttpService` / `OpenAIHttpService` filter `LLM_REQUEST` by `provider`; `tests/test_model_router_dispatch.py` |
| **S4** | SystemView poll race | **Done** | `system_view.py` `_poll_live()` + generation token; `tests/test_lifecycle_shutdown.py` |
| **S5** | State & lifecycle | **Done** | `application.shutdown()` → `state_store.close()`; palette destroy unsubscribes |
| **S6** | Observability | **Done** | `eventbus_topic_counts` in `system.snapshot`; `test_eventbus_topic_counts_in_system_snapshot` |
| **S7** | Settings / telemetry / tool_executor clarity | **Done** | Module docstrings; `ARCHITECTURE.md` settings chain; `requirements.txt` verified |
| **W4** | AppState domain split | **Partial** | `chat_state.py` + `workspace_state.py` + `model_state.py` + `tool_state.py` (slice 2); further splits deferred |

---

## Readiness verdict

| Question | Answer |
|----------|--------|
| **Program 3 dependency** | **Complete** — exit gate closed (WII ≥60%, adoption ~7.0); see `PROGRAM_3_WORKSPACE_ADOPTION.md` |
| **Backlog completion** | **100%** Program 1; Program 4 slices 1–3 landed |
| **Program 4 ready?** | **READY** — S1–S6 satisfied; slices 1–3 landed |

### Quality scores (1–10)

| Area | Score | Notes |
|------|-------|-------|
| S1 Execution reliability | 9 | Async `tool.invoke`; shell cancel on unload |
| S2 Shell hardening | 9 | Production sandbox + permission gate |
| S3 Model routing | 9 | Registry wired; dual subscribers remain but provider-gated |
| S4 UI runtime safety | 9 | Generation + mid-flight checks; Inspector UIQueue migration **done** (slice 3) |
| S5 State & lifecycle | 9 | Shutdown teardown verified |
| S6 Observability | 8 | Topic counters in system snapshot |
| S7 Dependency cleanup | 8 | Documented; `PluginManifest` dual-path retained by design |
| W4 AppState split | 9 | Chat + workspace + model + tool reducers |

---

## Program 4 slice 1 (2026-07-06)

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| Settings `model_tier_map` (schema v6) | **Done** | `settings_schema.py`, `migration_manager.py`, `tests/test_model_tier_map.py` |
| `ModelRouterService` tier routing | **Done** | `routing_tier` + `reasoning` tier from settings map |
| `model_state.py` AppState projection | **Done** | `MODEL_SELECTED` reducer; `AppState.model_selection` |
| Cross-platform `runtime_paths` | **Done** | Windows/macOS/Linux; `tests/test_runtime_paths.py` |

---

## Program 4 slice 2 (2026-07-06)

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| `tool_state.py` AppState projection | **Done** | `TOOL_STARTED` / `TOOL_COMPLETED` / `TOOL_FAILED` reducers; `recent_tool_runs` |
| Context budget tier downgrade (M2) | **Done** | `ModelRouterService` subscribes `context.over_budget`; assembler passes token budget |
| Tests | **Done** | `tests/test_context_budget_tier.py` |

---

## Program 4 slice 3 (2026-07-06)

| Deliverable | Status | Evidence |
|-------------|--------|----------|
| `HotkeyProvider` (Win/Linux/macOS/no-op) | **Done** | `platform/hotkey_provider.py`; `main.py` uses `overlay_hotkey`; `tests/test_hotkey_provider.py` |
| Workflow run persistence + replay | **Done** | `workflow_run_repository.py`, `workflow_persistence_service.py`, migration v6; `tests/test_workflow_persistence.py` |
| TD-05 Inspector → UIQueue | **Done** | `runtime_inspector.py`, `workspace_os_inspector.py`, `orchestration_inspector.py`; `main.py` marshals toggles via UIQueue; `tests/test_ui_queue.py` |

---

## Recommended Program 4 next slice

1. **Further W4 splits** — telemetry or orchestration projections if needed.
2. **macOS HotkeyProvider** — CGEvent tap behind `HotkeyProvider` (packaging track).

Do **not** start: semantic/vector memory, multi-agent expansion, or distributed execution until explicit gates in this doc and Appendix C pass.

---

## Program 4 slice 1 status

| Capability | Status |
|------------|--------|
| Model tiers | Implemented as settings-backed `model_tier_map` plus workspace task hints through `ModelRouterService` |
| Platform paths | Implemented in `platform.runtime_paths` for Windows `%APPDATA%`, Linux XDG, and macOS Application Support |

## Allowed after Program 3 midpoint

| Capability | Allowed scope |
|------------|---------------|
| Tool workflows | Tool-only workflow persistence and AppState projection |
| Plugin canvas entities | Publish plugin catalog items into Workspace OS entity topics |
| Large context | Entity graph assembly through EventBus before `ContextManager.build_context()` |

## Still gated after midpoint

| Capability | Gate |
|------------|------|
| Semantic/vector memory | Constitutional amendment plus UCGS profile update |
| Multi-agent runtime expansion | Appendix C sign-off in `ARCHITECTURE_TRANSITION_PLAN.md` |
| Agent workflow steps | Appendix C plus workflow contract review |
| Remote plugin marketplace/code loading | Plugin Runtime architectural review |
| Distributed/cloud execution | New cloud execution contract |

## Prepared code homes

| Module | Purpose |
|--------|---------|
| `ai_command_center.core.state.model_state` | `model.selected` AppState projection (**active** — slice 1) |
| `ai_command_center.core.state.tool_state` | `recent_tool_runs` AppState projection (**active** — slice 2) |
| `ai_command_center.repositories.workflow_run_repository` | Workflow run metadata persistence (**active** — slice 3) |
| `ai_command_center.platform.hotkey_provider` | Cross-platform overlay hotkey registration (**active** — slice 3) |
| `ai_command_center.core.state.chat_state` | Chat reducers (W4 — **active**) |
| `ai_command_center.core.state.workspace_state` | Workspace reducers (W4 — **active**) |

`tool_state` is active for `recent_tool_runs` projection (Program 4 slice 2).
