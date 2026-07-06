# Program 3 — Workspace Adoption Initiative

**Status:** Active tracked initiative (post–Program 2 Enforcement)  
**Authority:** Code-verified Workspace Adoption Plan (2026-07-06); `PROJECT_CONSTITUTION_V4.md` Invariant 13 (Host Platform Supremacy); `ARCHITECTURE_TRANSITION_PLAN.md` Program 3  
**Scope:** Shift center of gravity from chat-centric execution to workspace-centric execution — **no new platform features** until exit gate passes

> **Canonical detail for Program 3.** The transition plan retains the four-program master backlog; this document is the execution spec, exit gate, phased roadmap, and progress scorecard.

---

## Executive Summary

The codebase already implements the constitutional layer cake (`UI → AppState → EventBus → Services → Repositories → Storage`) and a functional Workspace OS shell (entities, bus handlers, `WorkspaceView`, `WorkspaceOsService`). Structural audits show, however, that **runtime execution remains chat-primary**: roughly **85–95%** of AI/command flows traverse `ui.command` → `command.routed` → chat handlers, with workspace scope optional rather than required. Workspace OS carries **~5–15% workspace runtime influence** today — strong skeleton, weak primary-runtime behavior (**Workspace Adoption Score: 3.5 / 10**).

Program 3 bridges the product identity gap between **AI Chat Application** (current) and **AI Command Center** (target). The constitutional mandate (Invariant 13) requires ACC to own workspace, orchestration, and authoritative state; external runtimes supply capabilities only. Adoption is therefore not a UI polish exercise — it is wiring **one active workspace scope** through every execution pillar so that commands, memory, sessions, context, and tools all resolve against the same workspace context before chat or models run.

**Success is measured structurally and by session telemetry:** workspace runtime influence rises from **≈5–15%** to **>60%**, and **all five completion pillars** execute through an **active workspace scope** (defined below). Program 4 (platform expansion) remains gated until this initiative reaches midpoint and exit criteria (`PROGRAM4_GATE_STATUS.md`).

---

## Success Metrics

| Metric | Current (code-verified) | Target (exit gate) | Measurement methodology |
|--------|-------------------------|--------------------|-------------------------|
| **Workspace runtime influence** | ≈5–15% | **>60%** | Composite **Workspace Influence Index (WII)** — §Influence Formula; corroborate with `compute_session_summary()` `workspace_scope.ratio_pct` (`telemetry_summary.py`) |
| **Workspace Adoption Score** | **3.5 / 10** | **≥7.0 / 10** | Five-dimension scorecard — §Adoption Score Trajectory |
| **Active workspace runtime** | `WorkspaceService.activate()` **unwired** (zero callers outside `workspace_service.py`) | `activate()` called on workspace selection; AppState holds `active_workspace_id` | Grep: `.activate(` callers; AppState snapshot field; `workspace.active` topic consumed |
| **Command spine scope** | `CommandRouterService._workspace_scope` copies optional fields (`command_router_service.py` L70–94); default intent `INTENT_CHAT` (L159) | ≥60% of `command.routed` events carry `workspace_id` from active scope | Telemetry `COMMAND_ROUTED` payloads; `tests/test_w1_workspace_routing.py` |
| **Memory scope** | `workspace_id` column exists; search unscoped when empty (`db/memory_repository.py` L79–88) | Remember/lookup default to active `workspace_id` | Integration tests; grep `workspace_id=` in `memory_graph_service.py` call paths |
| **Session scope** | `DEFAULT_CONVERSATION_ID` when no entity (`session_service.py` L93–103) | Active workspace entity drives default conversation | `entity_conversation_id` used for ≥60% of new sessions |
| **Context assembly** | `CapabilityContextAssembler` optional `ENTITY_CONTEXT_REQUEST` (L168–177); `workspace_id` only when present in payload (L141–145) | Assembler always receives active workspace + entity scope | `MEMORY_LOOKUP_REQUEST` / `SESSION_HISTORY_REQUEST` payloads include scope |
| **Tool execution** | `ShellToolService` publishes `tool.invoke` **without** `workspace_context` (`shell_tool_service.py` L43–52) | User and agent tools include `workspace_context` | Grep `workspace_context` on `TOOL_INVOKE`; `tests/test_program3_telemetry_scope.py` |
| **Service registration share** | 1 of 23 `BaseService` registrations when OS enabled (`service_factory.py` L156–225) — ~4% | N/A (secondary signal) | Factory count only; not sufficient alone for exit |
| **Governance** | Program 2 complete: UCGS block, empty arch lint baseline | No new service→service edges outside allowlist | `python tools/ucgs_runner.py`; `scripts/arch_lint.py` |

---

## Definition: Active Workspace Scope

An **active workspace scope** is the single authoritative runtime binding used by all five pillars. It is satisfied when **all** of the following hold simultaneously:

| Field | Source (target state) | Evidence today |
|-------|----------------------|----------------|
| `active_workspace_id` | `WorkspaceService.get_active()` → AppState projection | `_active_workspace_id` set only by `activate()` — never called |
| `workspace_id` on bus payloads | Propagated from active workspace on every scoped intent | Only when `UIController.current_workspace_scope()` returns `workspace_id` (entity `type == "workspace"`, `controller.py` L91–92) |
| `workspace_entity_*` | Active entity within workspace (card, resource, note projection) | Optional via `UI_OPEN_CHAT` → `chat_workspace_entity_*` (`chat_state.py`) |
| Scope inheritance | Card/resource chats inherit parent `workspace_id` | **Gap** — card chats may omit `workspace_id` for memory |

**Verifiable invariant (exit):** For any user-initiated command, memory operation, session read/write, context assembly, or tool invoke, the EventBus payload chain includes either `workspace_id` matching `AppState.active_workspace_id` or a resolvable `workspace_entity_id` whose parent workspace equals the active workspace.

---

## Completion Criteria (Exit Gate)

All checkboxes must pass before Program 3 is **complete**. Each pillar maps to audit classification **B→A** (workspace-aware → workspace-native entry).

### 1. Commands

- [x] `WorkspaceService.activate()` wired from workspace selection UI (`ui.workspace_os.*` or navigation)
- [x] `workspace.active` (or canonical `WORKSPACE_ACTIVATED`) defined in `core/events/topics.py` and subscribed by AppState
- [x] `UIController.publish_command` always merges `current_workspace_scope()` including `workspace_id` when active workspace set
- [ ] `CommandRouterService._workspace_scope` receives `workspace_id` on ≥60% of production `ui.command` flows (telemetry)
- [x] **Tests:** `tests/test_w1_workspace_routing.py` extended for active-workspace-default paths
- [ ] **Grep signal:** zero `ui.command` publish sites bypassing scope helper

### 2. Memory

- [x] `MemoryGraphService` defaults `workspace_id` to active workspace when payload omits it
- [x] `MEMORY_LOOKUP_REQUEST` from `CapabilityContextAssembler` always includes active `workspace_id`
- [x] Unscoped global search requires explicit opt-in (not default)
- [x] **Tests:** remember/lookup with active workspace and without explicit payload scope
- [ ] **Schema:** `workspace_id` populated on insert for ≥60% of new memory nodes in scoped sessions

### 3. Sessions

- [x] `SessionService._resolve_conversation_id` prefers active workspace entity over `DEFAULT_CONVERSATION_ID`
- [x] `UI_OPEN_CHAT` from workspace sets parent `workspace_id` on session scope (card/resource inheritance)
- [ ] New chat from command box uses active entity context when workspace has selection
- [x] **Tests:** per-entity `entity_conversation_id` is default when `active_workspace_id` set
- [ ] **Grep signal:** `DEFAULT_CONVERSATION_ID` not used as default when active workspace present

### 4. Context

- [x] `CapabilityContextAssembler.assemble_for_command` always publishes scoped `MEMORY_LOOKUP_REQUEST` and `SESSION_HISTORY_REQUEST`
- [x] `ENTITY_CONTEXT_REQUEST` fires for active workspace entity or primary selection
- [x] Workspace-level context aggregation available (Phase 3) — entity graph + relationships feed `ContextManager.build_context`
- [x] **Tests:** `tests/test_capability_context.py` with active workspace fixtures
- [ ] **Arch lint:** no new UI→service bypass of assembler for AI paths

### 5. Tools

- [x] `ShellToolService` includes `workspace_context` on every `TOOL_INVOKE` (mirror agent path in `tool_executor_service.py` L180–181)
- [ ] Tool results recorded on workspace timeline when `workspace_id` present
- [x] **Tests:** `tests/test_program3_telemetry_scope.py` — tool rows include scope
- [ ] **Grep signal:** `TOOL_INVOKE` without `workspace_context` limited to explicit user opt-out (documented)

### Cross-cutting exit checks

- [ ] **WII > 60%** on representative integration session (headless `create_application()` chat + workspace round-trip)
- [ ] **Workspace Adoption Score ≥ 7.0**
- [ ] Zero new direct service→service edges (Program 2 E4 allowlist holds)
- [ ] Legacy `EVENT_WORKSPACE_*` in `event_bus.py` migrated or aliased to `topics.py` constants
- [ ] `chat_state.py` + `workspace_state.py` reducers own scope fields (W4 partial — measure from S6 if available)

---

## Workspace Influence Index (WII) — Progress Formula

Structural estimate for **workspace runtime influence %** — not live QPS (no production topic counters yet). Use for milestone tracking between telemetry deployments.

### Pillar weights (sum = 100%)

| Pillar | Weight | Structural signal | Scoring rule (0–100 per pillar) |
|--------|--------|-------------------|--------------------------------|
| Commands | 25% | `command.routed` scope propagation | % of `COMMAND_ROUTED` handlers that read `workspace_id` or `workspace_entity_id` (9 subscribers today) × % payloads with scope |
| Memory | 15% | `memory_graph_service.py` + repository | 100 if default active `workspace_id`; 50 if opt-in only; 0 if global default |
| Sessions | 20% | `session_service.py` conversation resolution | 100 if active workspace drives default CID; scale by non-`default` conversation share |
| Context | 25% | `CapabilityContextAssembler` cascade | % of assemble paths publishing scoped lookup/history/entity requests |
| Tools | 15% | `shell_tool_service.py`, `tool_executor_service.py` | % of `TOOL_INVOKE` with `workspace_context` |

### Composite

```text
WII = 0.25×Cmd + 0.15×Mem + 0.20×Sess + 0.25×Ctx + 0.15×Tools
```

### Current baseline (code audit, 2026-07-06)

| Pillar | Estimate | Rationale |
|--------|----------|-----------|
| Commands | ~15% | Scope optional; `_workspace_scope` exists but no active workspace source |
| Memory | ~40% | Schema + opt-in propagation when scope present |
| Sessions | ~35% | Entity-scoped sessions exist; default `"default"` without entity |
| Context | ~30% | Assembler supports scope; not defaulted |
| Tools | ~10% | Agents/workflows scoped; user shell path not |
| **WII (composite)** | **~22%** | Aligns with audit **5–15%** influence band for execution paths; use conservative **≈10%** for reporting until Phase 1 lands |

### Telemetry corroboration (when sessions exist)

`TelemetryService` + `compute_session_summary()` → `workspace_scope.ratio_pct` counts session events with `workspace_id` or `entity_id` (`telemetry_summary.py` L224–237). Map: **ratio_pct ≥ 60** ⇒ necessary but not sufficient for exit (does not alone prove all five pillars).

---

## Workspace Adoption Score Trajectory

| Stage | Score | WII (approx) | Classification |
|-------|-------|--------------|----------------|
| **Today** | **3.5 / 10** | 5–15% | Emerging UI / experimental data plane |
| Phase 1 complete | 4.5 | 20–30% | Workspace-aware chat |
| Phase 2 complete | 5.5 | 30–40% | Active workspace runtime |
| Phase 3 complete | 6.0 | 40–50% | Context layer live |
| Phase 4–5 complete | 6.5–7.0 | 50–60% | Memory + tools scoped |
| **Program 3 exit** | **≥7.0** | **>60%** | **Core** — workspace-centric command center |
| Foundational (future) | ≥8.5 | ≥70% | All domains workspace-scoped |

### Score dimensions (audit weights)

| Dimension | Today | Exit target |
|-----------|-------|-------------|
| Infrastructure (entities, bus, services) | 6/10 | 8/10 |
| Runtime adoption (execution paths) | 2/10 | 8/10 |
| UI adoption | 5/10 | 7/10 |
| Governance/contract maturity | 3/10 | 7/10 |

---

## Phased Roadmap

Maps code-verified audit Phases 1–6 to completion pillars. **Do not skip Phase 1** — `activate()` + `active_workspace_id` is the highest-leverage change per audit Part 10.

### Phase 1 — Workspace-Aware Chat

| Attribute | Detail |
|-----------|--------|
| **Goal** | Bind active workspace; propagate `workspace_id` on commands, memory, sessions, context |
| **Pillars advanced** | Commands ●●●, Sessions ●●, Memory ●, Context ●● |
| **Effort** | **M** |
| **Risk** | **Medium** — `command.routed` contract touches 9 subscribers |

**Files affected**

| File | Change |
|------|--------|
| `ai_command_center/core/app_state.py` | `active_workspace_id` field + reducer |
| `ai_command_center/core/state/workspace_state.py` | Project active workspace |
| `ai_command_center/ui/controller.py` | `current_workspace_scope()` always includes active `workspace_id` |
| `ai_command_center/services/command_router_service.py` | `_workspace_scope` reads active scope defaults |
| `ai_command_center/core/capability_context_assembler.py` | Default `workspace_id` on memory/session requests |
| `ai_command_center/services/session_service.py` | Parent workspace for card/resource chats |
| `ai_command_center/ui/shell/view_manager.py` | Propagate parent workspace on `UI_OPEN_CHAT` |
| `ai_command_center/core/events/topics.py` | Add `WORKSPACE_ACTIVE` / `workspace.active` |
| `ai_command_center/core/workspace/workspace_service.py` | `activate()` called from bus handler |

**Services:** `WorkspaceService`, `CommandRouterService`, `SessionService`, `ChatHandlerService`  
**EventBus topics:** `workspace.active`, `workspace.activated` (canonical), `ui.command`, `command.routed`  
**AppState:** `active_workspace_id`, `chat_workspace_entity_*` alignment  

---

### Phase 2 — Workspace Entities

| Attribute | Detail |
|-----------|--------|
| **Goal** | Wire `WorkspaceService.activate()`; hierarchy and selection on canvas |
| **Pillars advanced** | Commands ●, Sessions ●, Context ● |
| **Effort** | **M** |
| **Risk** | **Low** |

**Files affected**

| File | Change |
|------|--------|
| `ai_command_center/core/workspace/workspace_service.py` | `activate()` / `deactivate()` bus-driven |
| `ai_command_center/core/entity/entity_bus_handlers.py` | Handler for workspace selection |
| `ai_command_center/ui/views/workspace_view.py` | Selection → activate |
| `ai_command_center/ui/workspace_os_controller.py` | Publish selection topic |
| `ai_command_center/core/state/workspace_state.py` | Hierarchy, selection |
| `ai_command_center/core/event_bus.py` | Consolidate legacy `EVENT_WORKSPACE_*` → `topics.py` |

**Services:** `WorkspaceOsService`, `EntityService`, `WorkspaceService`  
**EventBus topics:** `ui.workspace_os.*`, `workspace.create.request`, `entity.created`  
**AppState:** `workspace_os.entities`, `active_workspace_id`  

---

### Phase 3 — Workspace Context Layer

| Attribute | Detail |
|-----------|--------|
| **Goal** | Workspace-level context assembly; relationship traversal |
| **Pillars advanced** | Context ●●●, Commands ● |
| **Effort** | **L** |
| **Risk** | **High** — sync cascade contract (`CapabilityContextAssembler` docstring) |

**Files affected**

| File | Change |
|------|--------|
| `ai_command_center/core/capability_context_assembler.py` | Workspace aggregation entry point |
| `ai_command_center/core/events/topics.py` | `workspace.context.request` / `context.request` implementation |
| `ai_command_center/core/entity/relationship_service.py` | Graph traversal for context |
| `ai_command_center/core/entity/entity_bus_handlers.py` | Context handlers |
| `ai_command_center/services/chat_handler_service.py` | Consume workspace context bundle |

**Services:** New or extended context service; `RelationshipService`  
**EventBus topics:** `ENTITY_CONTEXT_REQUEST`, `workspace.context.*` (new)  
**AppState:** Context snapshot fields  

---

### Phase 4 — Workspace Memory

| Attribute | Detail |
|-----------|--------|
| **Goal** | Default memory scope to active workspace; entity-scoped keys |
| **Pillars advanced** | Memory ●●●, Context ● |
| **Effort** | **M** |
| **Risk** | **Medium** — schema migration |

**Files affected**

| File | Change |
|------|--------|
| `ai_command_center/services/memory_graph_service.py` | Active workspace default; entity keys |
| `ai_command_center/repositories/memory_repository.py` | Scoped search default |
| `ai_command_center/db/memory_repository.py` | `entity_id` column if added |
| `ai_command_center/repositories/database_bootstrap_repository.py` | Migration |
| `ai_command_center/core/app_state.py` | `memory_catalog` filter by workspace |

**Services:** `MemoryGraphService`  
**EventBus topics:** `memory.remember`, `memory.lookup.request`, `memory.select`  

---

### Phase 5 — Workspace Tool Execution

| Attribute | Detail |
|-----------|--------|
| **Goal** | All `tool.invoke` paths carry `workspace_context`; timeline integration |
| **Pillars advanced** | Tools ●●●, Commands ● |
| **Effort** | **M** |
| **Risk** | **Medium** — permission + sandbox interaction (Program 1 S2) |

**Files affected**

| File | Change |
|------|--------|
| `ai_command_center/services/shell_tool_service.py` | Add `workspace_context` to `TOOL_INVOKE` |
| `ai_command_center/services/tool_executor_service.py` | Validate scope; timeline publish |
| `ai_command_center/ui/shell/application_shell.py` | Scope on command-box tool paths |
| `ai_command_center/core/workspace_os_actions.py` | Bus-native tool path (defer direct OS calls per audit) |
| `ai_command_center/services/timeline_service.py` | Auto-record tool results |

**Services:** `ShellToolService`, `ToolExecutorService`, `TimelineService`  
**EventBus topics:** `tool.invoke`, `tool.result`, `timeline.record.request`  

---

### Phase 6 — Workspace-Centric Runtime

| Attribute | Detail |
|-----------|--------|
| **Goal** | Command spine requires active workspace; model/orchestration workspace inputs |
| **Pillars advanced** | All five ●●● |
| **Effort** | **XL** |
| **Risk** | **High** — breaking change to optional scope contract |

**Files affected**

| File | Change |
|------|--------|
| `ai_command_center/services/command_router_service.py` | Active workspace required for execution |
| `ai_command_center/services/orchestration_service.py` | Workspace-aware classify input |
| `ai_command_center/services/model_router_service.py` | Workspace/task hints |
| `ai_command_center/services/runtime_capability_router_service.py` | Scope on capability invoke |
| `ai_command_center/ui/shell/view_manager.py`, `ai_command_center/ui/app.py` | Routing policy — chat as consumer |

**Services:** All `COMMAND_ROUTED` subscribers (9 today), `ModelRouterService`, `OrchestrationService`  
**EventBus topics:** Full spine refactor  
**AppState:** W4 reducer split (`workspace_state.py`, `chat_state.py`, `tool_state.py`)  

**Phase 6a progress (2026-07-06):** Soft gate in `CommandRouterService` — execution intents (`chat`, `shell`, `agent`, memory, notes) publish `command.deferred` + `ui.workspace.required` when no active workspace; `INTENT_NAVIGATE` whitelisted. Auto-activate first workspace on `service.ready` (`workspace_os`). Tests: `tests/test_program3_phase6a.py`.

---

## Dependencies

| Dependency | Status | Requirement |
|------------|--------|-------------|
| **Program 1 — Stabilization** | Exit criteria met | Reliable execution before gravity shift |
| **Program 2 — Enforcement** | **Complete** | UCGS `enforcement_mode: block`; empty `arch_lint_baseline.json`; pre-commit + CI block |
| **W1–W4 backlog items** | Tracked in transition plan | W1→Phase 1–2; W2→Phases 1–4; W3→Phase 3; W4→Phase 6 + S6 measure |
| **S6 topic counters** | Optional accelerator | Feeds W4 measure-before-split |

Program 3 may overlap **late Program 2** only after Program 1 exit (per transition plan sequencing).

---

## Out of Scope / Defer

Per code-verified audit Part 10 — **do not implement during Program 3** unless explicitly pulled into a phase above:

| Item | Reason |
|------|--------|
| Full Phase 6 spine replacement before Phases 1–5 | Breaking; needs active workspace foundation first |
| Semantic / vector memory | Program 4 gate — constitutional amendment + UCGS profile (`PROGRAM4_GATE_STATUS.md`) |
| Multi-agent runtime expansion | Appendix C sign-off (`ARCHITECTURE_TRANSITION_PLAN.md`) |
| Workspace-driven model routing (tiers) | Program 4 — after midpoint |
| Replacing `workspace_os_actions.py` direct OS calls | Defer until tool bus contract stable (Phase 5) |
| Entity embeddings | Infrastructure stubbed only (`embedding_status` on Entity) |
| `CapabilityRouterService` (non-runtime) | **Not registered** in `service_factory.py` — ignore |
| Linux / macOS / MSI packaging | Program 4 |
| Plugin marketplace / code loading | Program 4 architectural review |

---

## Key Code Anchors (Audit Evidence)

| Finding | Location | Implication |
|---------|----------|-------------|
| `activate()` unwired | `workspace_service.py` L79–97; grep shows **zero external callers** | No active workspace runtime |
| Command scope helper | `command_router_service.py` L70–94 `_workspace_scope` | Scope propagation exists but optional |
| Default chat intent | `command_router_service.py` L159 `INTENT_CHAT` fallback | Chat-primary spine |
| Context assembler | `capability_context_assembler.py` L71–84, L141–177 | Optional entity + workspace scope |
| Memory propagation | `memory_graph_service.py` L91–97, L142–148, L176 | Scoped when payload present |
| Session default | `session_service.py` L93–103, L131 | `DEFAULT_CONVERSATION_ID` without entity |
| Shell tools unscoped | `shell_tool_service.py` L43–52 | No `workspace_context` on user shell |
| UI scope source | `controller.py` L81–101 `current_workspace_scope` | `workspace_id` only if entity type is `workspace` |
| Topics gap | `topics.py` — `WORKSPACE_CREATE_*` exist; no `workspace.active` | Legacy `EVENT_WORKSPACE_*` in `event_bus.py` L52–55 |
| Factory registration | `service_factory.py` L156–225 | 22 always-on services vs 1 `workspace_os` |
| Telemetry scope ratio | `telemetry_summary.py` L224–237; `tests/test_program3_telemetry_scope.py` | Session-level scoped event % |
| Parallel chat handlers | `chat_handler_service.py`, `orchestration_service.py`, `runtime_capability_router_service.py` on `COMMAND_ROUTED` | Fan-out bottleneck for scope contract changes |

---

## Governance Alignment

| Authority | Relevance |
|-----------|-----------|
| **Invariant 13** | ACC owns workspace and authoritative memory/conversation; adoption enforces supremacy |
| **Invariant 6** | Context assembly via EventBus cascade — extend, do not bypass `CapabilityContextAssembler` |
| **AGENTS.md Rule 3** | No service→service calls — workspace adoption via bus topics only |
| **Program 2 E4** | New direct service edges fail CI — bus-ify `WorkspaceOsService` island per W3 |
| **UCGS `ai-command-center` profile** | Run before architecture-sensitive commits; WARN review, FAIL block |

---

## W-Backlog Cross-Reference

Transition plan items map to this initiative:

| Item | Program 3 phase |
|------|-----------------|
| **W1** — Workspace entry routing | Phases 1–2 |
| **W2** — Domain re-homing | Phases 1, 4, 5 |
| **W3** — Context & bus-native WOS | Phases 2–3 |
| **W4** — AppState domain split | Phase 6 (after S6 measure) |

---

## Recommended First Implementation Slice

When coding is approved, start **Phase 1 only** (smallest vertical slice with highest leverage):

1. Add `WORKSPACE_ACTIVE` to `topics.py`; subscribe in `workspace_state.py` reducer.
2. Bus handler: workspace tile/select → `WorkspaceService.activate()`.
3. Project `active_workspace_id` in AppState; `UIController.current_workspace_scope()` reads it.
4. Extend `tests/test_w1_workspace_routing.py` — command + memory with active workspace default.
5. Run `python -m pytest tests/test_w1_workspace_routing.py tests/test_program3_telemetry_scope.py -q` and `python tools/ucgs_runner.py`.

**Do not** start Phase 6 or vector memory in the same PR.

---

## References

| Document | Role |
|----------|------|
| [ARCHITECTURE_TRANSITION_PLAN.md](ARCHITECTURE_TRANSITION_PLAN.md) | Master four-program backlog |
| [PROGRAM4_GATE_STATUS.md](PROGRAM4_GATE_STATUS.md) | Downstream gate |
| [WORKSPACE_VISION.md](WORKSPACE_VISION.md) | North-star vision |
| `PROJECT_CONSTITUTION_V4.md` | Invariant 13 |
| `tests/test_w1_workspace_routing.py` | W1 acceptance tests |
| `tests/test_program3_telemetry_scope.py` | Telemetry scope tests |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-06 | Phase 6a — workspace-required command spine (soft gate), auto-activate on boot |
| 2026-07-06 | Initial Program 3 tracked initiative — code-verified audit; >60% WII exit gate; five-pillar completion definition |
