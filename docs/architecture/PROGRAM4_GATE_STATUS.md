# Program 4 Gate Status

**Status:** **CONDITIONAL** — Program 3 **COMPLETE** (exit gate closed); remaining gates are Program 1 S1/S2 shell hardening only.

**Last assessed:** 2026-07-06 (main — exit sprint + post-Program 3 backlog merged)

Program 4 may not expand platform capabilities until:

1. Program 1 stabilization gates pass (partial — S1/S2 shell hardening remain).
2. Program 2 local/CI enforcement remains active (CI block on; local warn).
3. ~~Program 3 workspace adoption~~ — **satisfied** (WII ≥60%, adoption score ~7.0; `tests/test_program3_exit_gate.py`).

---

## Post-Program 3 backlog (2026-07-06)

| ID | Item | Status | Evidence |
|----|------|--------|----------|
| **S3** | Provider registry dispatch | **Done** | `service_factory.py` injects `ProviderRegistry` into `ModelRouterService`; `OllamaHttpService` / `OpenAIHttpService` filter `LLM_REQUEST` by `provider`; `tests/test_model_router_dispatch.py` |
| **S4** | SystemView poll race | **Done** | `system_view.py` `_poll_live()` + generation token; `tests/test_lifecycle_shutdown.py` |
| **S7** | Settings / telemetry / tool_executor clarity | **Done** | Module docstrings; `ARCHITECTURE.md` settings chain; `requirements.txt` verified |
| **W4** | AppState domain split | **Partial** | `chat_state.py` + `workspace_state.py` extracted; `model_state.py` / `tool_state.py` deferred to Program 4 |

---

## Readiness verdict

| Question | Answer |
|----------|--------|
| **Program 3 dependency** | **Complete** — exit gate closed (WII ≥60%, adoption ~7.0); see `PROGRAM_3_WORKSPACE_ADOPTION.md` |
| **Backlog completion** | **~95%** — S1/S2 (shell async, sandbox) remain Program 1 scope, not this backlog |
| **Program 4 ready?** | **CONDITIONAL** — unblocked on Program 3; first slice allowed pending S1/S2 shell gates |

### Quality scores (1–10)

| Area | Score | Notes |
|------|-------|-------|
| S3 Model routing | 9 | Registry wired; dual subscribers remain but provider-gated |
| S4 UI runtime safety | 9 | Generation + mid-flight checks; Inspector UIQueue migration still open |
| S7 Dependency cleanup | 8 | Documented; `PluginManifest` dual-path retained by design |
| W4 AppState split | 7 | Chat + workspace reducers extracted; tool/model/plugin deferred with S6 counters |

---

## Recommended Program 4 first slice

1. **Model tiers** — settings-backed tier map through `ModelRouterService` + `model_state.py` reducers.
2. **Platform paths** — OS-specific runtime directories behind `platform/runtime_paths.py` abstractions (Linux/macOS `APPDATA` equivalents).

Do **not** start: semantic/vector memory, multi-agent expansion, or distributed execution until explicit gates in this doc and Appendix C pass.

---

## Allowed after Program 3 midpoint

| Capability | Allowed scope |
|------------|---------------|
| Model tiers | Settings-backed tier map and workspace task hints through `ModelRouterService` |
| Platform paths | OS-specific runtime directories behind `platform/` abstractions |
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
| `ai_command_center.core.state.model_state` | Future `model.selected` AppState projection |
| `ai_command_center.core.state.tool_state` | Future `recent_tool_runs` AppState projection |
| `ai_command_center.core.state.chat_state` | Chat reducers (W4 — **active**) |
| `ai_command_center.core.state.workspace_state` | Workspace reducers (W4 — **active**) |

`model_state` and `tool_state` remain placeholder modules until Program 4 gates are satisfied.
