# AI Command Center — Architecture-First Repository Audit

| Field | Value |
|-------|-------|
| **Date** | 2026-08-28 |
| **Baseline** | `origin/main` @ `e0b8525a0cdc1b565bb4268bb34094822c8e68f1` |
| **Auditor role** | Principal Software Architect / Performance Engineer / Repository Auditor (Tom-compatible) |
| **Method** | Architecture-first (Phases 1–10). Code + headless measurement. No GUI soak (Linux x86_64 Cloud). |
| **Evidence hash** | `sha256:16065cf10ea9561e851cfff0159ac2c8534803813c86d5e63e52fc6c9718f4c5` (588 `ai_command_center/**/*.py`) |
| **Verdict** | **PARTIALLY_IMPLEMENTED** — core execution authority **conforms**; verified defects remain |
| **Overall score** | **72 / 100** |
| **Maturity** | **LEVEL_3** |

**Label legend:** **VERIFIED** = code or measurement. **MEASURED** = timed on this host. **INFERRED** = cost class without soak. **HYPOTHESIS** = plausible, not proven. **NOT VERIFIED** = incomplete evidence.

---

## 1. Executive Summary

AI Command Center on `main` @ `e0b8525` still implements its intended Workspace OS ownership and execution chain. **VERIFIED:** `ExecutionAuthorityService` is the sole live intake; `ExecutionOrchestratorService` is the sole production publisher of `tool.invoke`; shell execution uses `shell=False` + sandbox; receipt emit is fail-closed before `EXECUTION_RUN_COMPLETE`; AppState mutates only through reducers under `RLock`.

The repository does **not** fully meet peer Performance Constitution budgets or UI Rule 1 absolute isolation. **MEASURED:** `ui.command` → ExecutionAuthority sync publish averages ~7–11 ms (budget ≤5 ms SYNC_CRITICAL / Art IV). **VERIFIED:** `ToolExecutorService._execute_shell` blocks the async EventBus dispatch thread with `communicate(timeout=30)`. **VERIFIED:** secrets can fall back to plaintext settings SQLite; `qwenpaw_auth_token` never uses keyring. **VERIFIED:** UI opens YAML files and can call `os.startfile` / `webbrowser` outside Execution Authority.

**Do not redesign architecture.** Prefer repairing documented soft breaches, dispatch-thread blocking, secret handling, and stale docs. Win ARM64 UI soak remains **NOT VERIFIED** here.

---

## 2. Architecture Overview

### 2.1 Authorities read (Phase 1)

| Document | Role |
|----------|------|
| `PROJECT_CONSTITUTION_V4.md` | Supreme — Inv 1–13, Art XVII |
| `PERFORMANCE_CONSTITUTION.md` | Peer — budgets, anti-patterns |
| `docs/ARCHITECTURE.md` | Level 3 runtime map |
| `docs/ARCHITECTURE_ENFORCEMENT.md` | Level 2 agent rules |
| Accepted ADRs 001–025 (esp. 006, 018, 015–017, 007) | Binding decisions |
| `SCHEDULER_ABSTRACTION.md`, `RUNTIME_SAFETY.md`, `AGENT_RUNTIME_INTERFACE.md`, `ASYNC_EVENTBUS_POLICY.md`, `STATE_AUTHORITY_CONTRACT.md` | Runtime contracts |
| `ARCHITECTURE_DIAGRAM.md` | Diagram — **partially stale** (see findings) |

### 2.2 Intended ownership flow

```text
UI → AppState (projection) + EventBus (intent)
  → Services
  → Repositories
  → Storage (SQLite / files)
```

Live execution (ADR-006 / ADR-018):

```text
UI_COMMAND | WORKFLOW_EXECUTION_REQUEST | AGENT_EXECUTION_REQUEST
  → ExecutionAuthorityService (+ StateAuthority.project)
  → GOAL_SUBMIT_REQUEST {authority_decision}
  → SingleGoalScheduler
  → PLAN_REQUEST | synthetic PLAN_GENERATED
  → PlannerService (optional)
  → EXECUTION_RUN_REQUEST
  → ExecutionOrchestratorService  ⟵ sole TOOL_INVOKE publisher
  → ToolExecutorService | ChatHandler | CAPABILITY_RUNTIME_REQUEST
  → emit_execution_receipt (fail-closed) + OrchestrationService
  → AppState → UI
```

World Model mutation (current code truth):

```text
StateAuthorityService.mutate → WorldModel.apply
BrainRuntimeService._execute_action → WorldModel.apply
```

### 2.3 Dependency / ownership graph (verified)

```text
[UI Controllers / WorkspaceOsService]
        │ UI_COMMAND / WORKFLOW_EXECUTION_REQUEST
        ▼
[ExecutionAuthorityService] ──project──► [StateAuthorityService]
        │ GOAL_SUBMIT_REQUEST (+ authority_decision)
        ▼
[SingleGoalScheduler] ◄── GoalRepository
        │ PLAN_* / EXECUTION_RUN_REQUEST
        ▼
[ExecutionOrchestratorService] ══ sole TOOL_INVOKE / CAPABILITY_RUNTIME_REQUEST
        ├─► [ToolExecutorService] → sandbox / Popen(shell=False)
        ├─► [ChatHandlerService] → Ollama/OpenAI aiohttp loops
        └─► [QwenPawSidecarService] → sidecar Popen + HTTP
        ▼
 EXECUTION_RUN_COMPLETE|FAILED
        ├─► emit_execution_receipt → TruthBoundary topics
        └─► OrchestrationService → RUNTIME_ACTION_REQUEST
                                      ▼
                               [BrainRuntimeService] → WorldModel.apply

Parallel WM: [StateAuthorityService.mutate] → WorldModel.apply

Demoted / latent: OperatorKernel, OrchestrationExecutor, ShellProvider primary path,
                  ActionRegistry.invoke (bus path closed; API remains)
```

---

## 3. Repository Inventory

| Category | Count / notes | Evidence |
|----------|---------------|----------|
| Python modules (`ai_command_center/**/*.py`) | **588** | filesystem |
| Event topic string constants | **321** unique (`topics.py`) | static |
| BaseService-lineage classes | **45** (≤43 factory-wired) | `service_factory.py` |
| Managers | **8** (ServiceManager, ContextManager, MigrationManager, CapabilityLifecycleManager, UI managers) | inventory |
| Worker / background threads | **11** creator sites (EventBus dispatch, observer, obsidian, ollama/openai/qwenpaw loops, system monitor, telemetry, tray, hotkey, system_view) | code |
| `sqlite3.connect` | **2** (`db/connection.py:30`, federated WM read-only) | code |
| Repositories | `repositories/` + `db/` wrappers + entity/relationship/timeline under `core/` | inventory |
| Plugin manifests | **8** YAML under `plugins/` | inventory |
| Subprocess sites | **8** (tool shell, shell_provider, app launch, MCP, qwenpaw, workspace_os_actions, runtime_identity, linux hotkey) | grep |
| Network clients | aiohttp (3 services), httpx (3 adapters), urllib (detector) | inventory |
| `shell=True` / `os.system` / `eval` / `exec` / `requests` | **0** in package | grep |
| Timers | Tk `.after` ~24; `threading.Timer` (AppState coalesce, BrainRuntime) | inventory |

### Services (factory-wired, abbreviated)

ExecutionAuthority, SingleGoalScheduler, Planner, ExecutionOrchestrator, ToolExecutor, ToolRegistry, Orchestration, ChatHandler, OllamaHttp, OpenAIHttp, ModelRouter, Settings, Telemetry, Tracing, PluginRegistry, StateAuthority, BrainKernel/Runtime, Observer, Obsidian, SystemMonitor, WorkflowEngine/Persistence, AgentRuntime, QwenPawSidecar, RuntimeCapabilityRouter, RuntimeProviderRegistry, Federation, MemoryGraph, Session, ShellTool (metadata), CommandRouter, Artifact, OperationIndexer, CapabilityLifecycle, CapabilityPromptCatalog, ExternalCapabilityBridge, WorkspaceBootstrap, (+ optional WorkspaceOsService).

---

## 4. Verified Critical Issues

> Ranked by **architectural / runtime impact**, not lint severity. Tom taxonomy S1–S4.

### C1 — Shell `communicate` blocks EventBus async dispatch thread — **S1**

| Field | Detail |
|-------|--------|
| **File:line** | `ai_command_center/services/tool_executor_service.py:90–99` |
| **Function** | `_execute_shell` |
| **Call stack** | `TOOL_INVOKE` (ASYNC_ELIGIBLE) → `event-dispatch` thread → `ToolExecutorService._on_tool_invoke` → `ToolExecutor.execute` → `_execute_shell` → `Popen` + `communicate(timeout=30)` |
| **Why it matters** | Blocks **all** ASYNC_ELIGIBLE handlers for up to 30s (Perf Art X: long sync work / subprocess on shared dispatch path). |
| **Evidence** | Code; `dispatch_policy.py` lists `TOOL_INVOKE` in `ASYNC_ELIGIBLE_TOPICS`; handler calls `self._executor.execute` inline (`tool_executor_service.py:432`). |
| **Severity** | S1 (freeze/stall amplifier under shell load) |
| **Recommended fix** | Keep architecture: move shell wait off the dispatch thread (worker owned by ToolExecutorService) while retaining sole `TOOL_INVOKE` publisher and receipts. **Do not** invent a second executor. |
| **Status** | **VERIFIED** code path; freeze severity under real GUI **NOT VERIFIED** (no Win ARM64 soak). |

### C2 — SYNC_CRITICAL `ui.command` exceeds 5 ms budget — **S1**

| Field | Detail |
|-------|--------|
| **File:line** | `services/execution_authority_service.py` (`_on_ui_command`); topic `UI_COMMAND` in `dispatch_policy.py` SYNC_CRITICAL |
| **Call stack** | `bus.publish(UI_COMMAND, {text:…})` → sync handlers including EA → goal/plan/exec cascade |
| **Why it matters** | Performance Constitution Art III/IV: EventBus sync handler ≤5 ms; SYNC_CRITICAL policy ≤5 ms. |
| **Evidence** | **MEASURED** (APPDATA headless, `create_application` + startup): `{text: "list files"}` avg **6.97** ms, max **21.0** ms (n=20); `{text: "open notepad"}` avg **10.94** ms, max **25.6** ms. Empty/mis-keyed payloads stay &lt;0.1 ms (handler short-circuit). |
| **Severity** | S1 (budget violation on canonical intake) |
| **Recommended fix** | Measure → reduce work inside EA sync path (coalesce cascade publishes; defer non-critical projection). Do **not** flip topic out of SYNC_CRITICAL without approval (Perf Art X). |
| **Status** | **MEASURED** headless; Win GUI P99 **NOT VERIFIED**. |

---

## 5. Verified Major Issues

### M1 — Secrets plaintext fallback + token not in keyring — **S2**

| Field | Detail |
|-------|--------|
| **File:line** | `platform/secret_store.py:110–116`; `domain/settings_snapshot.py:76,92`; `services/settings_service.py:91–92,106–109`; `core/settings/settings_schema.py:67` |
| **Why it matters** | API keys/tokens can persist in SQLite and ride `settings.snapshot` / `SETTINGS_CHANGED` bus payloads. |
| **Evidence** | Keyring failure returns cleaned key for settings persistence; `to_payload()` includes `openai_api_key` and `qwenpaw_auth_token`; qwenpaw token never routed through keyring. |
| **Severity** | S2 |
| **Recommended fix** | Fail closed or encrypted store when keyring unavailable; route `qwenpaw_auth_token` through secret_store; redact secrets from bus payloads. |

### M2 — UI Rule 1 soft breaches (filesystem / OS open) — **S2**

| Field | Detail |
|-------|--------|
| **File:line** | `ui/views/workflow_graph_view.py:310,327` (`open` YAML); `ui/shell/application_shell.py:194` (`os.startfile`); `ui/runtime_inspector.py:308` (`webbrowser.open`); `ui/views/system_view.py` (psutil worker) |
| **Why it matters** | Constitution Inv 2 / Enforcement Rule 1: UI must not access files or OS capabilities directly; no ExecutionReceipt for toast/inspector opens. |
| **Evidence** | Direct `open`/`startfile`/`webbrowser` in UI package; no `sqlite3` under `ui/` (**UI→SQLite absent — good**). |
| **Severity** | S2 (isolation), not an alternate TOOL_INVOKE path |
| **Recommended fix** | Export/import and “open file” via EventBus → service → receipt where OS side effects matter; keep inspectors projection-only. |

### M3 — Duplicate shell implementations (live vs latent) — **S2**

| Field | Detail |
|-------|--------|
| **File:line** | Live: `tool_executor_service.py:43–122`. Latent: `orchestration/providers/shell_provider.py:18–87` |
| **Why it matters** | Drift risk; Inv 11 / non-circumvention if latent path is re-wired without EA. |
| **Evidence** | Near-duplicate `Popen` helpers; factory does not use ShellProvider as primary live shell. |
| **Severity** | S2 debt / latent authority |
| **Recommended fix** | Delete or demote paper provider to tests-only; single implementation module shared if tests need it. |

### M4 — Residual `ActionRegistry.invoke` callable in-process — **S2**

| Field | Detail |
|-------|--------|
| **File:line** | `core/action_registry.py` (invoke); bus redirect in `entity_bus_handlers.py` ~558+ |
| **Why it matters** | Live bus path closed, but in-process invoke can still run OS handlers without EA receipts if tests/callers misuse. |
| **Evidence** | Subagent + code comments: bus path redirected; walking-skeleton/tests still call invoke. |
| **Severity** | S2 latent |
| **Recommended fix** | Hard-disable invoke outside tests or assert receipt/EA context. |

---

## 6. Medium Issues

| ID | Finding | Evidence | Severity |
|----|---------|----------|----------|
| Med-1 | `ARCHITECTURE_DIAGRAM.md` still shows ShellToolService publishing `tool.invoke` | Diagram ~170–174 vs `shell_tool_service.py` docstring + EOS-only publishes | S3 doc drift |
| Med-2 | `RUNTIME_SAFETY.md` claims Runtime alone calls `worldModel.apply()` | Doc L8 vs SA `:436+` and BrainRuntime `:235` | S3 doc / contract drift |
| Med-3 | `docs/ARCHITECTURE.md` “EventBus sync today” vs `async_dispatch=True` | `application.py` factory; ASYNC policy doc | S3 |
| Med-4 | Dual AppState refresh (listener + EventCoordinator) for some topics | `ui/app.py`, `event_coordinator.py` | S3 residual PERF |
| Med-5 | AppState coalesce notify via `threading.Timer` may schedule Tk `after` off UI thread | `app_state.py:3838+` → `_queue_state_refresh` | S2 **HYPOTHESIS** freeze class (historical RCA; not re-proven) |
| Med-6 | CI performance tests weaker than Art IV (ui.command mean &lt;16 ms vs 5 ms) | pytest budgets | S3 gate gap |
| Med-7 | SA `submit_goal_for_state` bypasses bus `authority_decision` stamp | intentional ADR-016 path | S3 if UI ever reaches it — **HYPOTHESIS** misuse |

---

## 7. Low Issues

| ID | Finding | Evidence | Severity |
|----|---------|----------|----------|
| Low-1 | ~174 `except Exception`; ~78 swallowed `pass` | static inventory | S3/S4 |
| Low-2 | God files: `app_state.py` ~3912 LOC; orchestrator ~1254 LOC | LOC | S3 |
| Low-3 | ~19 unused topic consts; ~26 legacy `EVENT_*` only on `event_bus.py` | topics inventory | S4 |
| Low-4 | `goal_engine_repository` / StubOllama / notes re-export fossils | factory comments + tests | S4 |
| Low-5 | aiohttp one patch behind latest index | installed 3.14.1 vs 3.14.3 | S4; **CVE NOT VERIFIED** |
| Low-6 | UIQueue busy fallback 50 ms (idle 200 ms) | `ui_queue.py:14–15,96–103` | S4 tension with Art XVII spirit; idle OK |

---

## 8. Performance Report

### Budgets vs evidence

| Budget | Target | Result | Class |
|--------|--------|--------|-------|
| EventBus sync handler | ≤5 ms | `ui.command` avg 7–11 ms on EA path | **MEASURED FAIL** |
| EventBus publish | &lt;0.2 ms | Dominated by sync handler work on `ui.command` | **MEASURED FAIL** (EA path) |
| `settings.snapshot` publish | ≤5 ms | avg ~0.09–0.12 ms | **MEASURED PASS** |
| AppState reducer | ≤0.5 ms | avg ~0.08 ms (prior sample) | **MEASURED PASS** (headless) |
| AppState notify coalesce (`chat.chunk`) | ADR-007 | 100 chunks → 1 notify | **MEASURED PASS** |
| SQLite on UI thread | Forbidden | No sqlite in `ui/` | **VERIFIED PASS** |
| Tool shell on dispatch | Forbidden long block | `communicate(30)` on async dispatch | **VERIFIED FAIL** |
| UI thread / nav / inspector | Art III | — | **NOT VERIFIED** (no GUI) |
| PERF-001–004 Closed-DoD soak | Win ARM64 | Register: mitigated headless, soak operator-owned | **NOT VERIFIED** |
| PERF-005 SQLite contention | Open | Register | Open |

### Blocking call inventory (capability-related)

| Site | Thread | Cost class |
|------|--------|------------|
| `tool_executor_service._execute_shell` communicate | event-dispatch | up to 30s **VERIFIED** |
| Ollama/OpenAI HTTP | dedicated asyncio threads | off UI **VERIFIED** |
| Telemetry SQLite | batch worker | async **VERIFIED** |
| System monitor / system_view psutil | worker threads | **VERIFIED** |

---

## 9. Threading Report

| Role | Mechanism | Notes |
|------|-----------|-------|
| UI / Tk | CustomTkinter main | Windows ARM64 product; not runnable here |
| UIQueue | Virtual event + 50/200 ms fallback | Art XVII: event-driven; busy poll conditional |
| EventBus | `event-dispatch` daemon when `async_dispatch=True` | Default in `application.py` |
| AppState | RLock + Timer coalesce | Timer flush thread affinity risk (**HYPOTHESIS**) |
| LLM / sidecar | Dedicated asyncio loop threads + `.result(timeout=)` unload | Art XVII Finding 3 **HELD** |
| No ThreadPoolExecutor | — | **VERIFIED** absent in package |

**Cross-thread UI:** Inspectors/EventCoordinator use `ui_queue.enqueue` correctly. AppState → `_queue_state_refresh` may call `after()` without hop — **RISK**.

---

## 10. State Ownership Report

| Domain | Owner | Evidence |
|--------|-------|----------|
| Presentation projection | `AppStateStore` reducers only | `_state` assign only in `_on_event` |
| Workspace / WM / goals / memory mutations | `StateAuthorityService` (+ BrainRuntime for runtime actions) | `.apply` call sites |
| Settings SoT | Settings service + repository | schema + snapshot |
| Execution decisions | `ExecutionAuthorityService` | ADR-006 |
| Tool executability | Orchestrator → ToolExecutor (ADR-018) | sole `TOOL_INVOKE` publisher |

AppState: frozen dataclass snapshots; dirty identity check; coalesce only `chat.chunk`. **No** production direct `_state` writes outside store.

---

## 11. EventBus Report

| Item | Status |
|------|--------|
| Topic SoT | `core/events/topics.py` (321 unique) |
| Policy | `dispatch_policy.py` — SYNC_CRITICAL (13), ASYNC_ELIGIBLE (32) |
| Wildcard | Forbidden unless debug |
| Cycles | `ui.navigate` reentrancy drop |
| Sole `TOOL_INVOKE` publisher | `ExecutionOrchestratorService` lines **689**, **750** |
| Subscribers of `TOOL_INVOKE` | ToolExecutorService (execute), AgentRuntime (observe), Telemetry |
| Dead / alias topics | `TELEMETRY_EVENTS` alias; unused reserved state.context.*; legacy EVENT_* on event_bus |
| Sync bottlenecks | EA on `ui.command`; settings fan-in OK |

---

## 12. Security Report

| Area | Verdict |
|------|---------|
| Shell injection | `shell=False` + CommandSandbox **VERIFIED** |
| Secret storage | Keyring preferred; **plaintext fallback** **VERIFIED** |
| QwenPaw token | Settings field only — **VERIFIED** gap |
| Bus leakage | Snapshot payloads include key/token fields **VERIFIED** |
| Temp files | None in package **VERIFIED** |
| At-rest encryption | None (SQLite plaintext) **VERIFIED** |
| Permissions | PermissionService + security tiers on TOOL_INVOKE **VERIFIED** present |
| Logging secrets | No direct `api_key=` log lines found; payload logging **HYPOTHESIS** risk |

---

## 13. Dependency Report

| Package | Pin | Installed | Note |
|---------|-----|-----------|------|
| customtkinter | ≥5.2 | 6.0.0 | OK |
| aiohttp | ≥3.9 | 3.14.1 | 1 patch behind latest index |
| httpx | ≥0.28.1 | 0.28.1 | OK |
| keyring | ≥24 | 25.7.0 | OK |
| keyboard | ≥0.13.5 | 0.13.5 | aged; **CVE NOT VERIFIED** |
| Pillow | ≥10 | 12.3.0 | **CVE NOT VERIFIED** |
| OTel | ≥1.20 | 1.44.0 | **CVE NOT VERIFIED** |

No advisory database consulted → **all CVE claims NOT VERIFIED**.

---

## 14. Constitutional Compliance

| Invariant / rule | Verdict | Notes |
|------------------|---------|-------|
| Inv 1 Ownership flow | **MOSTLY HELD** | Persistence/services OK; UI soft file/OS opens |
| Inv 2 UI isolation | **PARTIAL** | No SQLite/Ollama from UI; file/OS/psutil soft breaches |
| Inv 3 EventBus governance | **HELD** | Dual legacy EVENT_* registry debt |
| Inv 4 AppState presentation | **HELD** | |
| Inv 5 Repository ownership | **HELD** | UI has no repo imports |
| Inv 6 ContextManager | **HELD** for AI path (spot-check; full matrix **NOT VERIFIED**) |
| Inv 9 Telemetry firewall | **HELD** (observe-only by design; deep proof **NOT VERIFIED**) |
| Inv 11 SoT integrity | **PARTIAL** | Dual WM apply is Accepted SA/Brain split; diagram/RUNTIME_SAFETY stale |
| Inv 12 Non-circumvention | **PARTIAL** | Latent ActionRegistry / ShellProvider |
| Inv 13 Host supremacy | **HELD** | Sidecar capability-only; ACC SoT |
| Art XVII UIQueue | **HELD** with conditional 50 ms busy fallback |
| Art XVII shutdown `.result()` | **HELD** for HTTP sidecars |
| ADR-006 EA sole intake | **HELD** | OperatorKernel not factory-wired |
| ADR-018 sole TOOL_INVOKE | **HELD** | EOS only |
| Perf Art X anti-patterns | **FAIL** on shell-dispatch block + sync budget | |

**Axes (Tom):**

| Axis | Process | Outcome |
|------|---------|---------|
| Architecture authority chain | PASS | PASS |
| Performance budgets | PASS (docs/gates exist) | FAIL (measured) / UNPROVEN (GUI soak) |
| UI isolation absolute | PASS (rules) | FAIL (soft breaches) |
| Security secrets | PARTIAL | FAIL (fallback) |
| Closed-DoD soak | N/A | UNPROVEN |

---

## 15. Technical Debt

1. Oversized AppState + ExecutionOrchestrator modules  
2. Broad `except Exception` / swallowed errors  
3. Duplicate shell + dual HTTP stacks (aiohttp services vs httpx adapters)  
4. Dual metrics collectors (SystemMonitorService + SystemView psutil)  
5. Stale diagrams / Phase-0 Proposed docs treated as current  
6. Fossil goal_engine / stub paths  
7. Weaker CI perf gates than Constitution Art IV  

**Features requiring redesign:** **None identified as necessary.** Defects are repairable within current architecture.

---

## 16. Recommended Priority Order

1. **P0** — Offload shell `communicate` from EventBus dispatch thread (preserve EA→EOS→ToolExecutor).  
2. **P0** — Reduce `ui.command` / EA sync-path work to meet ≤5 ms (measure-driven; no topic policy flip).  
3. **P1** — Secret handling: no plaintext SQLite fallback; keyring for qwenpaw token; redact bus payloads.  
4. **P1** — Close UI Rule 1 soft breaches (workflow YAML, startfile, align SystemView with SystemMonitor).  
5. **P2** — Remove or quarantine latent ShellProvider / ActionRegistry.invoke.  
6. **P2** — Align `ARCHITECTURE_DIAGRAM.md`, `RUNTIME_SAFETY.md`, ARCHITECTURE EventBus wording with code.  
7. **P3** — Tighten CI budgets toward Art IV; Win ARM64 soak for PERF-001–004 Closed-DoD.  
8. **P3** — Gradual god-file / exception-handling debt reduction (no drive-by refactors).  

---

## Phase appendices (compressed)

### Execution Authority verification

| Check | Result |
|-------|--------|
| Exactly one live intake | **VERIFIED** EA on UI_COMMAND / workflow / agent requests |
| Bypasses | UI OS opens (soft); SA submit_goal (ADR-016); latent ActionRegistry |
| TOOL_INVOKE publishers | **Only** EOS `:689`, `:750` |

### Scheduler

| Concern | Result |
|---------|--------|
| Ownership | `SingleGoalScheduler` |
| Concurrency | Single active goal; priority queue |
| Cancel / pause / resume | Present |
| Retry | **None** automatic |
| Duplicates | No title dedupe |
| authority_decision gate | **VERIFIED** refuse without stamp (`goal_scheduler_service.py:264–275`) |

### Capability runtime / receipts

| Check | Result |
|-------|--------|
| Paths | ToolExecutor, ChatHandler, QwenPaw CAPABILITY_RUNTIME, launch tools |
| Receipts | `emit_execution_receipt` fail-closed before COMPLETE (`execution_orchestrator_service.py:1170–1199`) |
| Missing receipts | UI startfile/webbrowser; paper OrchestrationExecutor |

### Call graphs (critical)

```text
UI → UI_COMMAND → ExecutionAuthority → GOAL_SUBMIT → Scheduler
  → EXECUTION_RUN → Orchestrator → TOOL_INVOKE → ToolExecutor → shell Popen
  → RUN_COMPLETE → emit_execution_receipt → AppState

BYPASS (soft): UI toast → os.startfile (no EA/receipt)
BYPASS (latent): ActionRegistry.invoke / ShellProvider (not factory live)
```

### Code quality rank (impact)

1. Dispatch-thread shell + sync budget (architecture/runtime)  
2. Secrets bus/SQLite  
3. UI isolation soft breaches  
4. Latent duplicate executors  
5. Exception swallowing / god files  

### Falsification attempt

Attacked COMPLIANT verdict by searching for alternate `TOOL_INVOKE` publishers, `shell=True`, UI→sqlite, and OperatorKernel factory wiring. **No second live TOOL_INVOKE publisher and no UI→sqlite found.** Bypass evidence is soft UI OS I/O, plaintext secrets, and dispatch-thread blocking — enough to refuse COMPLIANT, not enough to claim NEEDS_REDOING of the authority model.

---

## Deduction rubric (Tom)

Start: **100**

| ID | Deduction | Reason |
|----|-----------|--------|
| D1 | −8 | Shell blocks async dispatch (S1) |
| D2 | −7 | SYNC_CRITICAL `ui.command` over budget (S1 MEASURED) |
| D3 | −5 | Secret plaintext / token gap (S2) |
| D4 | −4 | UI Rule 1 soft breaches (S2) |
| D5 | −3 | Stale authority docs / dual latent shell (S3) |
| D6 | −1 | Code quality / fossils (S3/S4) |

**Overall: 72** → **PARTIALLY_IMPLEMENTED** / **LEVEL_3**

### Dimension scores (weighted → Σ ≈ 72)

| Dimension | Weight | Score | Contribution |
|-----------|--------|-------|--------------|
| architecture_compliance | 20 | 85 | 17.0 |
| plan_adherence (Accepted ADRs) | 15 | 82 | 12.3 |
| implementation_completeness | 15 | 78 | 11.7 |
| code_quality | 15 | 62 | 9.3 |
| maintainability | 10 | 60 | 6.0 |
| scalability | 5 | 70 | 3.5 |
| testability | 5 | 75 | 3.75 |
| ui_consistency | 5 | 70 | 3.5 |
| performance | 5 | 55 | 2.75 |
| technical_debt | 5 | 50 | 2.5 |
| **Σ** | 100 | — | **72.3** |

---

## Machine-Readable Verification Block

```json
{
  "tom_verification_block": true,
  "verdict": "PARTIALLY_IMPLEMENTED",
  "overall_score": 72,
  "repo_commit": "e0b8525a0cdc1b565bb4268bb34094822c8e68f1",
  "evidence_hash": "sha256:16065cf10ea9561e851cfff0159ac2c8534803813c86d5e63e52fc6c9718f4c5",
  "file_count_checked": 588,
  "critical_failures": 2,
  "falsification_attempted": true,
  "falsification_vector": "search for alternate TOOL_INVOKE publishers, shell=True, UI→sqlite, OperatorKernel factory wiring",
  "ci_enforced_lock": false
}
```
