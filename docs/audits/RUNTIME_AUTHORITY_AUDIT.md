# Runtime Authority Audit

**Status:** Completed (evidence only — no wiring changes)  
**Milestone:** `PHASE_0R_REPOSITORY_TRUTH_RECONCILIATION.md`  
**Baseline:** `origin/main` @ `c4a88f4` (`docs/audits/REPOSITORY_TRUTH_CANON.md` merged via #82)  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `docs/ARCHITECTURE_ENFORCEMENT.md`, `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md`  

---

## 1. Scope and methodology

This audit traces the live runtime authority path for operator-facing actions on `origin/main`:

```text
UI intent → EventBus → service_factory wiring → authority services → execution → receipt → verification
```

Files inspected:

- `ai_command_center/application.py` (composition root entry)
- `ai_command_center/core/service_factory.py` (service construction)
- `ai_command_center/operator/kernel.py` (OperatorKernel)
- `ai_command_center/ui/shell/application_shell.py` (command box)
- `ai_command_center/ui/controller.py` (UI_COMMAND publisher)
- `ai_command_center/services/command_router_service.py` (intent routing)
- `ai_command_center/services/chat_handler_service.py` (chat path)
- `ai_command_center/services/orchestration_service.py` (truth-bound orchestration)
- `ai_command_center/services/runtime_capability_router_service.py` (external runtime routing)
- `ai_command_center/services/agent_runtime_service.py` (agent spawn/run)
- `ai_command_center/services/ollama_http_service.py` / `openai_http_service.py` (LLM consumers)
- `ai_command_center/services/model_router_service.py` (model resolution)
- `ai_command_center/orchestration/agents/agent_coordinator.py`
- `ai_command_center/orchestration/goals/planning_engine.py`
- `ai_command_center/core/world_model/predictive_engine/`
- `ai_command_center/core/world_model/undo_replay/`
- `ai_command_center/platform/hotkey_provider.py`
- `ai_command_center/platform/platform_service.py`
- `tests/test_operator/test_kernel_integration.py`
- `tests/test_operator/test_golden_validation_suite.py`

Probe technique: `grep` for class instantiation in `service_factory.py`, `grep` for `subscribe(<topic>)` in runtime services, and manual trace of `COMMAND_ROUTED` / `LLM_REQUEST` / `EXECUTION_RUN_REQUEST` consumers.

---

## 2. Composition root (`application.py` + `service_factory.py`)

### 2.1 Entry point

`application.py:52` `create_application()`:

```python
def create_application(
    *,
    debug_mode: bool = False,
    workspace_os_enabled: bool = True,
    db: sqlite3.Connection | None = None,
) -> ApplicationCore:
    db = db or init_database()
    bus = EventBus(debug_mode=debug_mode, async_dispatch=True)
    state_store = AppStateStore(bus)
    wired = build_services(db, bus, workspace_os_enabled=workspace_os_enabled)
    return ApplicationCore(...)
```

`ApplicationCore.startup()` (`application.py:38`) loads the `ServiceManager`, then publishes `app.phase` ready. No `OperatorKernel` is constructed or loaded.

### 2.2 What `build_services()` wires

`core/service_factory.py:129` constructs and registers the following runtime-relevant services:

| Service | Line | Registered | Notes |
|---------|------|------------|-------|
| `PermissionService` | 170 | Yes | Wired with `wire_bus_handlers()` |
| `ToolRegistryService` | 174 | Yes | |
| `ToolExecutorService` | 175 | Yes | |
| `BrainRuntimeService` | 195 | Yes | |
| `BrainKernelService` | 196 | Yes | |
| `GoalEngine` | 197 | Yes | Matrix: **WIRED** |
| `PlannerService` | 203 | Yes | |
| `ExecutionOrchestratorService` | 204 | Yes | |
| `ExternalCapabilityBridgeService` | 205 | Yes | Matrix: **WIRED** |
| `ExecutionRunService` / `ExecutionQueryService` | 206-212 | Yes | |
| `OperationIndexerService` | 213 | Yes | |
| `ModelRouterService` | 224 | Yes | Subscribes `MODEL_RESOLVE_REQUEST`, not `LLM_REQUEST` |
| `AgentRuntimeService` | 225 | Yes | Subscribes `COMMAND_ROUTED` for `INTENT_AGENT` |
| `WorkflowEngineService` | 226 | Yes | |
| `RuntimeProviderRegistryService` | 229 | Yes | |
| `RuntimeCapabilityRouterService` | 235 | Yes | Subscribes `COMMAND_ROUTED` for `INTENT_CHAT` |
| `OrchestrationService` | 241 | Yes | Subscribes `COMMAND_ROUTED` for `INTENT_CHAT` / `INTENT_SHELL` |
| `OllamaHttpService` | 166 / 277 | Yes | Subscribes `LLM_REQUEST` |
| `OpenAIHttpService` | 167 / 278 | Yes | Subscribes `LLM_REQUEST` |
| `ChatHandlerService` | 283 | Yes | Subscribes `COMMAND_ROUTED` for `INTENT_CHAT` |
| `WorkspaceOsService` | 322 | Yes (if enabled) | |

### 2.3 What `build_services()` does **not** wire

| Capability | Exists on `main` | Wired in factory | Evidence |
|------------|------------------|------------------|----------|
| `OperatorKernel` | `ai_command_center/operator/kernel.py:83` | **No** | No import/construct in `service_factory.py` or `application.py`; only used in `tests/test_operator/` |
| `AgentCoordinator` | `ai_command_center/orchestration/agents/agent_coordinator.py:53` | **No** | No factory reference |
| `PlanningEngine` | `ai_command_center/orchestration/goals/planning_engine.py:99` | **No** | No factory reference |
| `PredictiveEngine` | `ai_command_center/core/world_model/predictive_engine/` | **No** | Package exists; not imported in factory |
| `UndoReplay` | `ai_command_center/core/world_model/undo_replay/` | **No** | Package exists; not imported in factory |
| `PlatformService` concrete implementations | `ai_command_center/platform/platform_service.py` | **No** | `PlatformService` is an ABC; tray/hotkey not wired into startup |

This matches the matrix entries: `OperatorKernel`, `AgentCoordinator`, `PlanningEngine`, `Predictive engine`, `Undo / replay` are **PARTIAL**; platform tray/hotkey is **MISSING/STUB**.

---

## 3. Command path trace

### 3.1 UI origin

- `ui/shell/application_shell.py:225` `_on_command(text, ...)`
- `ui/shell/application_shell.py:270` calls `self._controller.publish_command(text, clipboard=..., workspace_entity=...)`
- `ui/controller.py:151` `publish_command()` builds payload from workspace scope and publishes `UI_COMMAND` (`ui/controller.py:186-190`).

### 3.2 Router (`CommandRouterService`)

- `services/command_router_service.py:82-83` subscribes `UI_COMMAND` → `_on_ui_command`.
- `services/command_router_service.py:145` `_on_ui_command` classifies text into one of `INTENT_CHAT`, `INTENT_SHELL`, `INTENT_AGENT`, `INTENT_NAVIGATE`, `INTENT_NOTE_*`, `INTENT_MEMORY_*`.
- `services/command_router_service.py:184-195` publishes `COMMAND_ROUTED` with intent, args, workspace scope.

This is the **single routing point** for typed/palette input. All downstream consumers listen to `COMMAND_ROUTED`.

### 3.3 Downstream consumers of `COMMAND_ROUTED`

Three services subscribe to `COMMAND_ROUTED` for chat/shell/agent intents. They are all loaded simultaneously and rely on early-return guards and request-id markers to avoid duplicate handling:

| Service | Subscribed at | Intent filter | Behavior |
|---------|---------------|---------------|----------|
| `OrchestrationService` | `orchestration_service.py:101-103` | `INTENT_CHAT`, `INTENT_SHELL` | Classifies with `RuleBasedIntentClassifier`; if a provider matches, runs `OrchestrationExecutor` and emits `ORCHESTRATION_RECEIPT` + `ORCHESTRATION_TRUTH_VALIDATED` + `CHAT_COMPLETE` |
| `RuntimeCapabilityRouterService` | `runtime_capability_router_service.py:122-125` | `INTENT_CHAT` | Classifies `CapabilityKind` (planning, coding, research, agents, memory, chat); resolves provider; if non-native, assembles context and invokes external runtime provider; falls back to native via `CAPABILITY_FALLBACK` |
| `ChatHandlerService` | `chat_handler_service.py:73-75` | `INTENT_CHAT` | Assembles context with `CapabilityContextAssembler`; if not handled by orchestration/external, publishes `LLM_REQUEST` |
| `AgentRuntimeService` | `agent_runtime_service.py:79-80` | `INTENT_AGENT` | Spawns/executes demo or real agent pipelines, publishes tool events |

### 3.4 LLM execution path

- `ChatHandlerService` → `CapabilityContextAssembler.assemble_for_command()` → `ContextBundle` with prompt, sources, token estimate.
- `ChatHandlerService:235` publishes `LLM_REQUEST`.
- `OllamaHttpService:79` and `OpenAIHttpService:78` subscribe `LLM_REQUEST` and perform actual HTTP streaming.
- They emit `LLM_CHUNK`, `LLM_COMPLETE`, `LLM_ERROR`.
- `ChatHandlerService` and orchestration/response composers translate `LLM_*` events into `CHAT_CHUNK`, `CHAT_COMPLETE`, `CHAT_ERROR` for the UI.

**No `OperatorKernel.process()` is invoked anywhere in this path.**

### 3.5 Shell execution path

- `OrchestrationService._on_command_routed` (`orchestration_service.py:145-150`) handles `INTENT_SHELL`.
- `OrchestrationService._orchestrate_shell` (`orchestration_service.py:214-385`) enforces workspace, classifies intent, runs `OrchestrationExecutor` with provider `shell`, validates through `TruthBoundary`, publishes `ORCHESTRATION_RECEIPT`, `ORCHESTRATION_TRUTH_VALIDATED`, `ORCHESTRATION_RUN_SNAPSHOT`, `CHAT_COMPLETE`.

**No `OperatorKernel` or `ShellToolService` is the first authority gate.** `ShellToolService` exists and is registered, but is reached through `TOOL_INVOKE` from `ExecutionOrchestratorService` / `AgentRuntimeService`, not directly from the UI command path.

### 3.6 Agent execution path

- `AgentRuntimeService._on_command_routed` (`agent_runtime_service.py:149`) handles `INTENT_AGENT`.
- It spawns pipelines or single agents, publishes `AGENT_SPAWNED`, `AGENT_PIPELINE_STARTED`, `AGENT_PIPELINE_STAGE`, `AGENT_TASK_REQUEST`, `TOOL_INVOKE`, `TOOL_RESULT`.
- `ExecutionOrchestratorService` (`execution_orchestrator_service.py:59-74`) subscribes `EXECUTION_RUN_REQUEST` and `TOOL_RESULT` for approved planner manifests.

**No `AgentCoordinator` is used.** The agent runtime does its own task/pipeline management.

---

## 4. Answers to 0R audit questions

### Q1: Does every action flow through the intended architecture?

**No. The intended authority chain is bypassed in several places.**

| Intended authority | Actual live path | Finding |
|--------------------|------------------|---------|
| `OperatorKernel` should classify intent, resolve mode, assemble prompts, invoke model, validate compliance | `CommandRouterService` → `ChatHandlerService` / `OrchestrationService` / `RuntimeCapabilityRouterService` directly | `OperatorKernel` is not constructed or subscribed |
| `PlanningEngine` should generate/validate plans from goals | `PlannerService` + `GoalEngine` | `PlanningEngine` not wired; plans are produced by `PlannerService` (heuristic) and executed by `ExecutionOrchestratorService` |
| `AgentCoordinator` should assign tasks to agents | `AgentRuntimeService` | `AgentCoordinator` not wired; agent runtime manages tasks internally |
| `PredictiveEngine` / `UndoReplay` should support world-model operations | Not in command path | Packages exist, not in factory |
| Cross-platform hotkey + tray should be live OS surface | `get_hotkey_provider()` returns `MacOSHotkeyProvider` placeholder on macOS; `PlatformService` abstract, no concrete impl wired | Partial / missing |

### Q2: Where does composition bypass planned kernels (`OperatorKernel`)?

The bypass is at **the composition root** and **every command consumer**:

1. **Factory bypass** — `service_factory.py` does not import `ai_command_center.operator` or construct `OperatorKernel`.
2. **Chat bypass** — `ChatHandlerService` calls `CapabilityContextAssembler` + publishes `LLM_REQUEST` directly, never `OperatorKernel.process(OperatorRequest(...))`.
3. **Orchestration bypass** — `OrchestrationService` uses `RuleBasedIntentClassifier` and `OrchestrationExecutor` directly, not `OperatorKernel`.
4. **Capability bypass** — `RuntimeCapabilityRouterService` classifies capabilities and invokes external providers directly, not `OperatorKernel`.
5. **Model invocation bypass** — `OllamaHttpService` / `OpenAIHttpService` subscribe `LLM_REQUEST`; `OperatorKernel._invoke_model()` expects a `ModelAdapter` that is never configured in the live path.
6. **Agent bypass** — `AgentRuntimeService` handles `INTENT_AGENT` without `AgentCoordinator`.
7. **Shell bypass** — `OrchestrationService` handles `INTENT_SHELL` directly, while `OperatorKernel` has no shell-specific contract.

### Q3: Which “old services” remain the live path?

The currently live services (all constructed in `service_factory.py`) are:

- `CommandRouterService` — intent classification and `COMMAND_ROUTED` emission
- `ChatHandlerService` — native chat context assembly + `LLM_REQUEST`
- `OllamaHttpService` / `OpenAIHttpService` — actual LLM HTTP streaming
- `OrchestrationService` — truth-bound intent routing and shell/chat execution
- `RuntimeCapabilityRouterService` — external runtime provider dispatch
- `AgentRuntimeService` — agent spawn/run/demo pipelines
- `ExecutionOrchestratorService` — step-by-step plan execution with approval gates
- `ExecutionRunService` / `ExecutionQueryService` — execution persistence/queries
- `ModelRouterService` — model tier resolution on `MODEL_RESOLVE_REQUEST`
- `BrainRuntimeService` / `BrainKernelService` / `GoalEngine` / `PlannerService` — wired, mostly feeding state snapshots

`OperatorKernel`, `AgentCoordinator`, `PlanningEngine`, `PredictiveEngine`, and `UndoReplay` are **not** in the live path.

---

## 5. Live command path diagrams

### Chat (native)

```text
ApplicationShell._on_command(text)
  → UIController.publish_command()
    → Event: UI_COMMAND
      → CommandRouterService._on_ui_command()
        → Event: COMMAND_ROUTED (intent=INTENT_CHAT)
          → ChatHandlerService._on_command_routed()
            → CapabilityContextAssembler.assemble_for_command()
              → Event: LLM_REQUEST
                → OllamaHttpService / OpenAIHttpService._on_llm_request()
                  → Events: LLM_CHUNK / LLM_COMPLETE / LLM_ERROR
                    → UI: CHAT_CHUNK / CHAT_COMPLETE
```

### Chat (truth-bound / orchestration)

```text
... COMMAND_ROUTED (INTENT_CHAT)
  → OrchestrationService._on_command_routed()
    → RuleBasedIntentClassifier.classify(query)
      → IntentRouter.resolve_provider(intent)
        → OrchestrationExecutor.run()
          → Event: ORCHESTRATION_RECEIPT
            → TruthBoundary.validate()
              → Event: ORCHESTRATION_TRUTH_VALIDATED
                → ResponseComposer.compose()
                  → Event: CHAT_COMPLETE
```

### Chat (external runtime)

```text
... COMMAND_ROUTED (INTENT_CHAT)
  → RuntimeCapabilityRouterService._on_command_routed()
    → classify(query) → CapabilityKind
      → resolve_provider(kind)
        → RuntimeProvider.invoke(invocation)
          → (external sidecar / MCP / etc.)
            → on failure: CAPABILITY_FALLBACK
```

### Shell

```text
... COMMAND_ROUTED (INTENT_SHELL)
  → OrchestrationService._orchestrate_shell()
    → workspace gate
      → OrchestrationExecutor.run(provider="shell")
        → ORCHESTRATION_RECEIPT + TRUTH_VALIDATED + CHAT_COMPLETE
```

### Agent

```text
... COMMAND_ROUTED (INTENT_AGENT)
  → AgentRuntimeService._on_command_routed()
    → spawn / pipeline / task demo logic
      → Events: AGENT_* + TOOL_INVOKE / TOOL_RESULT
        → ExecutionOrchestratorService (for approved manifests)
```

### Expected (but not live) OperatorKernel path

```text
... UI_COMMAND
  → CommandRouterService (or a future OperatorKernel entry)
    → OperatorKernel.process(OperatorRequest(...))
      → IntentResolver.resolve()
      → ModeResolver.resolve()
      → PromptAssemblyService.assemble()
      → ModelAdapter.complete()
      → ComplianceEngine.validate()
      → OperatorResponse
        → routed to Chat / Shell / Agent / Plan execution
```

This path is implemented in `operator/kernel.py` but is **not connected** to `service_factory.py`.

---

## 6. Matrix alignment (selected rows)

| Capability | Matrix status | Evidence from this audit | Verdict |
|------------|---------------|--------------------------|---------|
| `OperatorKernel` | **PARTIAL** (exists ✅, wired ❌, tests-only ⚠️) | `operator/kernel.py` present; no factory/startup wiring; tests in `tests/test_operator/` | Confirmed |
| `AgentCoordinator` | **PARTIAL** | `orchestration/agents/agent_coordinator.py` present; not in factory; `AgentRuntimeService` replaces it in live path | Confirmed |
| `PlanningEngine` | **PARTIAL** | `orchestration/goals/planning_engine.py` present; not in factory; `PlannerService` + `ExecutionOrchestratorService` are live | Confirmed |
| `Predictive engine` | **PARTIAL** | package exists; not in factory | Confirmed |
| `Undo / replay` | **PARTIAL** | package exists; not in factory (only `register_timeline_undo_handlers` for workspace OS is wired) | Confirmed |
| `ExecutionAuthority` | **WIRED** | `ExecutionOrchestratorService`, `ExecutionRunService`, `ExecutionQueryService` registered; `OrchestrationService` uses `TruthBoundary` | Confirmed |
| `StateAuthority` | **WIRED** | `AppStateStore`, `SystemSnapshotBuilder`, `StateApplierMixin` in UI | Confirmed |
| `Cross-platform hotkey (macOS)` | **PARTIAL** | `MacOSHotkeyProvider` placeholder; `get_hotkey_provider()` returns it on darwin | Confirmed |
| `Platform tray / notifications` | **MISSING/STUB** | `PlatformService` is ABC; no concrete impl wired; `NotImplementedError` in stubs | Confirmed |

---

## 7. Risks and implications

| # | Risk | Why it matters |
|---|------|----------------|
| 1 | `OperatorKernel` exists but is not the system of record | Architecture docs describe the kernel as the “single source of operational behavior.” The live app uses ad-hoc classifiers and HTTP services instead, so behavior rules, compliance gates, and response contracts are duplicated or skipped. |
| 2 | Three competing `COMMAND_ROUTED` consumers for chat | `OrchestrationService`, `RuntimeCapabilityRouterService`, and `ChatHandlerService` all listen. Dispatch order and `is_orchestration_handled()` / `is_externally_handled()` guards determine the winner. This is fragile and can produce inconsistent behavior when intents are borderline. |
| 3 | `PlanningEngine` / `AgentCoordinator` bypassed | Multi-agent planning is a Phase 9 objective, but the orchestration runtime does not use the existing engines. This makes Phase 9 completion claims unverifiable from the product path. |
| 4 | `PredictiveEngine` / `UndoReplay` not wired | World-model advanced features are not reachable from `create_application()`, so they are dead code from a runtime authority perspective. |
| 5 | `ModelRouterService` is not on the LLM path | It handles `MODEL_RESOLVE_REQUEST` but `ChatHandlerService` resolves model/provider inside `CapabilityContextAssembler`. The model router is therefore not authoritative for chat. |
| 6 | Platform integration is stubbed | macOS hotkeys and tray are placeholders; `PlatformService` has no concrete implementation wired. Cross-platform parity is documentation-only. |
| 7 | `OperatorKernel` unit tests give false confidence | `tests/test_operator/` exercise `OperatorKernel.process()` with injected mocks, but because the kernel is not wired, those tests do not prove the product path. |

---

## 8. Wiring gap backlog (Guardian-managed)

Ordered by authority risk. **Devin implements only when a row is explicitly assigned as the active gap.**

| Priority | Gap | Suggested wiring (not implemented) |
|----------|-----|------------------------------------|
| 1 | `OperatorKernel` not in composition root | Construct `OperatorKernel` in `service_factory.py`, inject `ModelAdapter` (or route to `OllamaHttpService`/`OpenAIHttpService` adapter), and make it the single authority for `INTENT_CHAT` / `INTENT_SHELL` / `INTENT_AGENT` handling. |
| 2 | `AgentCoordinator` not wired | Replace or wrap `AgentRuntimeService` task assignment with `AgentCoordinator`; register coordinator in factory. |
| 3 | `PlanningEngine` not wired | Route goal/plan requests through `PlanningEngine` before `ExecutionOrchestratorService`; wire into factory. |
| 4 | `PredictiveEngine` / `UndoReplay` not wired | Add world-model service wiring and EventBus topics so workspace OS operations can use predictive/undo features. |
| 5 | `ModelRouterService` not on LLM path | Either route `LLM_REQUEST` through `ModelRouterService` or remove/adapt its contract. |
| 6 | `COMMAND_ROUTED` multi-consumer race | Define a single dispatcher (likely `OperatorKernel` or a dispatcher service) that decides among orchestration, external capability, native chat, and agent paths, instead of three independent consumers. |
| 7 | macOS hotkey + tray | Implement and wire `MacOSHotkeyProvider` and a concrete `PlatformService` (or honest matrix downgrade). |

---

## 9. Reproduction commands

```bash
# Confirm OperatorKernel is not in factory/application
grep -R "OperatorKernel" ai_command_center/core/service_factory.py ai_command_center/application.py || echo "NO factory wiring"

# Confirm live LLM consumers
grep -n "subscribe(LLM_REQUEST" ai_command_center/services/*.py

# Confirm COMMAND_ROUTED consumers
grep -n "subscribe(COMMAND_ROUTED" ai_command_center/services/*.py

# Confirm OperatorKernel test-only usage
grep -R "OperatorKernel" tests/test_operator/

# Confirm AgentCoordinator / PlanningEngine are not wired
grep -R "AgentCoordinator\|PlanningEngine" ai_command_center/core/service_factory.py ai_command_center/application.py || echo "NO factory wiring"
```

---

## 10. Summary

- **UI → EventBus** is healthy: `CommandRouterService` is the single `UI_COMMAND` consumer and emits `COMMAND_ROUTED`.
- **EventBus → service factory** is partially healthy: many services are wired, but `OperatorKernel`, `AgentCoordinator`, `PlanningEngine`, `PredictiveEngine`, and `UndoReplay` are absent from `build_services()`.
- **Authority → execution** is fragmented: three services compete to handle `COMMAND_ROUTED` chat intents, and the LLM call is made directly by `OllamaHttpService`/`OpenAIHttpService` without the kernel’s governance pipeline.
- **Execution → receipt → verification** exists through `OrchestrationService` (`TruthBoundary` + `ResponseComposer`), but it bypasses the kernel.
- **Bottom line:** `OperatorKernel` is the largest **exists-but-not-wired** authority gap. The runtime is functional today because older/ad-hoc services cover the same surface, but the kernel is not the live path.
