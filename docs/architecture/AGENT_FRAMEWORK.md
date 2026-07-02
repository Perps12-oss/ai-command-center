# Agent Framework

**Status:** Architecture Specification  
**Vision ref:** [WORKSPACE_VISION.md](WORKSPACE_VISION.md) — Agents  
**Constitutional refs:** No direct service-to-service calls; PermissionService gate

---

## Purpose

Specify a bus-native multi-agent runtime where agents are supervised EventBus participants, not background threads with direct service access.

---

## Current State

| Asset | Status |
|-------|--------|
| Event topics `agent.spawned`, `agent.terminated` | Defined in `core/event_bus.py` |
| `AICapabilityRegistryService` | Registers AI-executable actions |
| `PermissionService` | Gates action invocation |
| Agent runtime | **Not implemented** — gated per ARCHITECTURE.md 6.5 |

---

## Target Architecture

```mermaid
flowchart TB
    subgraph UI
        CP[Command Palette]
    end
    subgraph Bus
        AS[agent.spawned]
        AT[agent.task.request]
        AC[agent.task.complete]
        AX[agent.terminated]
    end
    subgraph Services
        AR[AgentRuntimeService]
        PR[PermissionService]
        TE[ToolExecutorService]
        CH[ChatHandlerService]
    end
    CP -->|ui.command| AR
    AR --> AS
    AR -->|permission.check| PR
    AR -->|tool.invoke| TE
    AR -->|command.routed chat| CH
    AR --> AC
    AR --> AX
```

---

## Agent Lifecycle

| State | Entry | Exit |
|-------|-------|------|
| `SPAWNING` | `agent.spawn.request` | `agent.spawned` |
| `RUNNING` | task assigned | task complete or cancel |
| `WAITING` | blocked on tool/LLM | result received |
| `TERMINATED` | timeout, cancel, complete | `agent.terminated` |

Agents carry: `agent_id`, `parent_workspace_id`, `capabilities[]`, `request_id` correlation.

---

## Phases

| Phase | Deliverable | Acceptance |
|-------|-------------|------------|
| **A0** | Topic + domain model `AgentSession` | Dataclass in `domain/` |
| **A1** | Single supervised agent (chat wrapper) | Spawn → one task → terminate |
| **A2** | Tool-using agent loop | Max N tool invokes per spawn |
| **A3** | Multi-agent with workspace scope | Entities link agent runs to cards |

---

## Constitutional Compliance

- Agents **publish** tool and chat intents; never import repositories
- All AI paths through ContextManager
- Permission denied → `permission.denied` + agent error state
- Telemetry: `telemetry.event` for spawn/complete/fail

---

## Risks

| Risk | Mitigation |
|------|------------|
| Runaway agent loops | Hard cap on steps; `agent.cancel.request` |
| Permission escalation | PermissionService mandatory pre-flight |
| UI thread blocking | AgentRuntime runs on worker; UI via AppState only |

---

## Acceptance Criteria (A1)

- [ ] `AgentRuntimeService` registered in service_factory
- [ ] Spawn/terminate visible in AppState + timeline
- [ ] No direct imports between AgentRuntime and ChatHandler
- [ ] `verify_phase*` script or pytest coverage for happy path
