Status: ARCHIVED
Archive-class: SUPERSEDED
Superseded-by: ai_command_center/services/agent_runtime_service.py + orchestration/agents/* (different design)
Main-sha: e128a72
Verified-by: docs/audits/PHASE_PLANS_ARCHIVE_VERIFICATION.md
Do-not-plan-from: true

# Phase 7: Multi-Agent Runtime

**Status:** GATED  
**Priority:** MEDIUM  
**Estimated Effort:** 4-6 weeks  
**Dependencies:** Phase 5 (Async), Phase 6 (External Bridge)  
**Authority:** `AGENTS.md`, `AGENT_RUNTIME_INTERFACE.md`, `PROJECT_CONSTITUTION_V4.md`

---

## Constitutional Gate Checklist

**Before any multi-agent code, ALL questions below must be answered:**

### A1 — Context Before Conversation

- [ ] Which service owns agent context assembly?
- [ ] EventBus topic + payload for context request/result?
- [ ] How is `ContextManager` bypass prevented?

### A2 — Execution Before Explanation

- [ ] Minimum executable artifact before `chat.complete` / UI explanation?
- [ ] Topics that mark execution vs narration?

### A5 — Determinism Before AI

- [ ] Deterministic fallback when agent fails?
- [ ] Commands never routed to agents?
- [ ] How is agent output verified/sandboxed before affecting workspace?

### System-level

- [ ] Multi-agent must be opt-in
- [ ] `CommandRouterService` must not be shadowed by agent dispatch

---

## Architecture

### Agent Lifecycle

```text
Spawn → Context Assembly → Task Assignment → Execution → Verification → Response
   │              │                  │             │              │
   ▼              ▼                  ▼             ▼              ▼
agent.spawned  agent.context   agent.task.   execution.*    chat.complete
               .request        assigned
```

### EventBus Topics

| Topic | Direction | Payload |
|-------|-----------|---------|
| `agent.spawned` | Outbound | `{ agent_id, config, workspace_scope }` |
| `agent.context.request` | Inbound | `{ agent_id, scope }` |
| `agent.context.result` | Outbound | `{ agent_id, context_bundle }` |
| `agent.task.assigned` | Inbound | `{ agent_id, task_id, capability, args }` |
| `agent.task.completed` | Outbound | `{ agent_id, task_id, result, verified }` |
| `agent.terminated` | Outbound | `{ agent_id, reason }` |

---

## Ownership Rules

```text
UI → AppState → EventBus → Services → Repositories → Storage
```

- **FORBIDDEN:** Agent direct access to files, SQLite, settings, Ollama, or tools
- **FORBIDDEN:** Direct service-to-service calls
- **ALLOWED:** `AppState` + `SettingsSnapshot` only
- **ALLOWED:** EventBus publish/subscribe only

---

## Implementation

### 7.1 Agent Registry Service

**File:** `ai_command_center/services/agent_registry_service.py`

**Responsibilities:**
- Track active agents
- Manage agent lifecycle
- Enforce permission gates

### 7.2 Agent Context Assembler

**File:** `ai_command_center/services/agent_context_service.py`

**Responsibilities:**
- Subscribe to `agent.context.request`
- Assemble context via `ContextManager`
- Publish `agent.context.result`

### 7.3 Agent Task Executor

**File:** `ai_command_center/services/agent_task_executor_service.py`

**Responsibilities:**
- Subscribe to `agent.task.assigned`
- Route to appropriate capability
- Publish `agent.task.completed`

### 7.4 Verification Gate

**File:** `ai_command_center/services/agent_verification_service.py`

**Responsibilities:**
- Validate agent output before workspace mutation
- Check against execution policy
- Block unverified changes

---

## Files

### Create

```
ai_command_center/services/agent_registry_service.py
ai_command_center/services/agent_context_service.py
ai_command_center/services/agent_task_executor_service.py
ai_command_center/services/agent_verification_service.py
ai_command_center/domain/agent.py
tests/test_agent_registry_service.py
tests/test_agent_lifecycle.py
tests/test_agent_verification.py
```

### Modify

```
ai_command_center/core/events/topics.py
ai_command_center/services/capability_prompt_catalog_service.py
```

---

## Required Deliverables (Gate Sign-off)

1. [ ] Data-flow diagram: spawn → context → execute → result
2. [ ] EventBus topics + payloads (new or existing)
3. [ ] Service decomposition diagram
4. [ ] Constitutional question → design decision mapping
5. [ ] Forbidden execution paths list
6. [ ] Verification plan (tests, scripts, gates)

### Sign-off Checklist

- [ ] Author date / name
- [ ] Reviewer name
- [ ] Constitutional compliance confirmed (yes / no)
- [ ] Recommendation: proceed or revise

---

## Testing

### Unit Tests

- [ ] `test_agent_spawn_and_terminate`
- [ ] `test_agent_context_assembly`
- [ ] `test_agent_task_execution`
- [ ] `test_agent_verification_blocks_untrusted`

### Integration Tests

- [ ] `test_agent_lifecycle_full_flow`
- [ ] `test_agent_permission_gates`
- [ ] `test_agent_workspace_isolation`

---

## Exit Criteria

- [ ] Constitutional gate sign-off
- [ ] All architectural guarantee tests pass
- [ ] Permission-gated agent spawning
- [ ] Context assembly through `ContextManager` only
- [ ] Architecture lint clean
- [ ] UCGS PASS

---

## Non-Goals

- Autonomous ReAct loops (User Goal → Plan → Execute → Stop only)
- Agent-to-agent communication
- Agent persistence beyond session

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial plan (gated) |
