# Blueprint AppState Projection Verification Report

**Audit Date:** 2026-07-13  
**Auditor:** Tom (Senior Engineering Auditor)  
**Repository:** ai-command-center  
**Source Commit:** 335a0aa (feat(blueprint-phase8): AppState PermissionCheckSnapshot projection)

---

## Executive Summary

This report documents the comprehensive verification of all 7 Blueprint AppState Snapshot projections. Each snapshot is analyzed for:

- Authoritative owner
- Repository owner  
- Startup rehydration path
- Event publishers
- Reducer consumers
- Persistence path
- Recovery path
- Constitutional compliance

**Verified Defects:**
1. **DEFECT 1:** WorldModelSnapshot - No startup rehydration (WORLD_MODEL_GRAPH_REFRESHED never published)
2. **DEFECT 2:** ExecutionLibrarySnapshot - No startup rehydration (no EXECUTION_RUNS_LOADED)
3. **DEFECT 3:** WorkflowLibrarySnapshot - total_started idempotency bug (always increments)

---

## Snapshot-by-Snapshot Analysis

---

### 1. WorldModelSnapshot

| Property | Value | Evidence |
|----------|-------|----------|
| **Authoritative Owner** | EntityService, RelationshipService | `core/entity/entity_service.py:27-36` |
| **Repository Owner** | `entity_repository`, `relationship_repository` | `core/entity/entity_repository.py`, `core/relationship/relationship_repository.py` |
| **Startup Rehydration** | ❌ NONE | `WORLD_MODEL_GRAPH_REFRESHED` is never published |
| **Event Publishers** | `EntityService`, `RelationshipService` | Publish `ENTITY_CREATED`, `ENTITY_UPDATED`, `ENTITY_DELETED` |
| **Reducer Consumer** | `_reduce_world_model` | `core/app_state.py:1835` |
| **Persistence Path** | EntityRepository → EntityService → EventBus | ✅ Full path exists |
| **Recovery Path** | ❌ BROKEN | No bulk load event at startup |
| **Snapshot Authoritative?** | ❌ NO | Projection only - repository is authoritative |
| **Projection Only?** | ✅ YES | Immutable snapshot from events |
| **Constitutional Risk** | ⚠️ MEDIUM | No history rebuild on restart |

**DEFECT 1 CONFIRMED:**
```python
# Source: core/events/topics.py:373
WORLD_MODEL_GRAPH_REFRESHED = "world_model.graph.refreshed"
```

Search for publisher: `grep -rn "publish.*WORLD_MODEL_GRAPH_REFRESHED" ai_command_center`
Result: **NO PUBLISHER FOUND** - topic defined but never emitted

**Event Flow (Partial - Runtime Only):**
```
User creates entity
  → EntityService.create()
    → EntityRepository.create()
    → EntityService._event_bus.publish(ENTITY_CREATED, {...})
      → _reduce_world_model() subscribes
        → NodeSnapshot added to world_model.nodes
```

**Missing Startup Flow:**
```
Application startup
  → ? (no service publishes WORLD_MODEL_GRAPH_REFRESHED)
    → AppState.world_model = WorldModelSnapshot() (empty)
      → UI shows empty world model
```

---

### 2. CapabilityLibrarySnapshot

| Property | Value | Evidence |
|----------|-------|----------|
| **Authoritative Owner** | RuntimeProviderRegistryService | `services/runtime_provider_registry_service.py` |
| **Repository Owner** | `runtime_provider_manifest_repository` | `repositories/runtime_provider_manifest_repository.py` |
| **Startup Rehydration** | ✅ YES | `_publish_providers_ready()` in `_on_load` |
| **Event Publishers** | `RuntimeProviderRegistryService` | Publish `CAPABILITY_PROVIDERS_READY` |
| **Reducer Consumer** | `_reduce_capability_library` | `core/app_state.py:2638` |
| **Persistence Path** | RuntimeProviderManifestRepository → Service → EventBus | ✅ Full path exists |
| **Recovery Path** | ✅ WORKING | Published on service load |
| **Snapshot Authoritative?** | ❌ NO | Projection only |
| **Projection Only?** | ✅ YES | Immutable snapshot |
| **Constitutional Risk** | ✅ LOW | Properly wired |

**Startup Flow Verified:**
```python
# Source: services/runtime_provider_registry_service.py:97-126
def _publish_providers_ready(self) -> None:
    providers: list[dict[str, object]] = []
    for provider_id in self._registry.list_ids():
        provider = self._registry.get(provider_id)
        # ... build payload
    self._bus.publish(
        CAPABILITY_PROVIDERS_READY,
        {"providers": providers},
        source=self.name,
    )
```

---

### 3. ExecutionLibrarySnapshot

| Property | Value | Evidence |
|----------|-------|----------|
| **Authoritative Owner** | ExecutionOrchestratorService | `services/execution_orchestrator_service.py` |
| **Repository Owner** | `execution_run_repository` | `repositories/execution_run_repository.py` |
| **Startup Rehydration** | ❌ NONE | `ExecutionRunService` does NOT publish `EXECUTION_RUNS_LOADED` |
| **Event Publishers** | `ExecutionOrchestratorService` | Publish `EXECUTION_RUN_STARTED`, `EXECUTION_STEP_*` |
| **Reducer Consumer** | `_reduce_execution_library` | `core/app_state.py:2497` |
| **Persistence Path** | ExecutionRunRepository ← ExecutionRunService | Repository exists, service subscribes only |
| **Recovery Path** | ❌ BROKEN | No rehydration event |
| **Snapshot Authoritative?** | ❌ NO | Projection only |
| **Projection Only?** | ✅ YES | Immutable snapshot |
| **Constitutional Risk** | ⚠️ HIGH | History lost on restart |

**DEFECT 2 CONFIRMED:**
```python
# Source: services/execution_run_service.py:23-29
def _on_load(self) -> None:
    self._unsubscribers.append(
        self._bus.subscribe(ORCHESTRATION_RUN_SNAPSHOT, self._on_orchestration_snapshot)
    )
    self._unsubscribers.append(
        self._bus.subscribe(CHAT_COMPLETE, self._on_chat_complete)
    )
    # NO _publish_recent_runs() call!
```

Compare with `WorkflowPersistenceService` which DOES publish:
```python
# Source: services/workflow_persistence_service.py:43
def _on_load(self) -> None:
    # ... subscriptions ...
    self._publish_recent_runs()  # <-- ExecutionRunService missing this!
```

---

### 4. AgentPipelineSnapshot

| Property | Value | Evidence |
|----------|-------|----------|
| **Authoritative Owner** | AgentRegistry | `orchestration/agents/agent_registry.py` |
| **Repository Owner** | ❌ NONE | No AgentRunRepository exists |
| **Startup Rehydration** | ❌ NONE | No agent history persistence |
| **Event Publishers** | `AgentRegistry`, `AgentRuntimeService` | Publish `AGENT_SPAWNED`, `AGENT_TERMINATED` |
| **Reducer Consumer** | `_reduce_agent_pipeline_snapshot` | `core/app_state.py:2357` |
| **Persistence Path** | ❌ BROKEN | No repository for agent runs |
| **Recovery Path** | ❌ N/A | No persistence layer |
| **Snapshot Authoritative?** | ❌ NO | In-memory only |
| **Projection Only?** | ⚠️ PARTIAL | In-memory projection with no persistence |
| **Constitutional Risk** | ⚠️ HIGH | Agent runs not persisted |

**Gap:** `AgentRegistry` maintains in-memory `_agents` dict with no persistence:
```python
# Source: orchestration/agents/agent_registry.py:59
self._agents[agent.id] = agent  # In-memory only
```

---

### 5. ProviderRegistrySnapshot

| Property | Value | Evidence |
|----------|-------|----------|
| **Authoritative Owner** | RuntimeProviderRegistryService | `services/runtime_provider_registry_service.py` |
| **Repository Owner** | `runtime_provider_manifest_repository` | `repositories/runtime_provider_manifest_repository.py` |
| **Startup Rehydration** | ✅ YES | Same as CapabilityLibrarySnapshot |
| **Event Publishers** | `RuntimeProviderRegistryService` | Publish `CAPABILITY_PROVIDERS_READY` |
| **Reducer Consumer** | `_reduce_provider_registry` | `core/app_state.py:2269` |
| **Persistence Path** | RuntimeProviderManifestRepository → Service → EventBus | ✅ Full path |
| **Recovery Path** | ✅ WORKING | Published on service load |
| **Snapshot Authoritative?** | ❌ NO | Projection only |
| **Projection Only?** | ✅ YES | Immutable snapshot |
| **Constitutional Risk** | ✅ LOW | Properly wired |

---

### 6. WorkflowLibrarySnapshot

| Property | Value | Evidence |
|----------|-------|----------|
| **Authoritative Owner** | WorkflowEngineService | `services/workflow_engine_service.py` |
| **Repository Owner** | `workflow_run_repository` | `repositories/workflow_run_repository.py` |
| **Startup Rehydration** | ✅ YES | `WorkflowPersistenceService._publish_recent_runs()` |
| **Event Publishers** | `WorkflowEngineService`, `WorkflowPersistenceService` | Publish `WORKFLOW_STARTED`, `WORKFLOW_RUNS_LOADED` |
| **Reducer Consumer** | `_reduce_workflow_library` | `core/app_state.py:2107` |
| **Persistence Path** | WorkflowRunRepository → WorkflowPersistenceService → EventBus | ✅ Full path |
| **Recovery Path** | ✅ WORKING | Published on service load |
| **Snapshot Authoritative?** | ❌ NO | Projection only |
| **Projection Only?** | ✅ YES | Immutable snapshot |
| **Constitutional Risk** | ⚠️ MEDIUM | Idempotency bug in total_started |

**DEFECT 3 CONFIRMED - Idempotency Bug:**
```python
# Source: core/app_state.py:2169-2174
if not any(r.run_id == run_id for r in runs):
    runs = runs + (run,)
    # ... cap history ...
else:
    runs = tuple(r if r.run_id != run_id else run for r in runs)
new_lib = replace(
    lib,
    runs=runs,
    active_run_id=run_id,
    total_started=lib.total_started + 1,  # BUG: Always increments!
)
```

**Correct behavior should be:**
```python
new_lib = replace(
    lib,
    runs=runs,
    active_run_id=run_id,
    total_started=lib.total_started + (1 if prev is None else 0),
)
```

---

### 7. PermissionCheckSnapshot

| Property | Value | Evidence |
|----------|-------|----------|
| **Authoritative Owner** | PermissionService | `core/permission/permission_service.py` |
| **Repository Owner** | ❌ NONE | No PermissionCheckRepository exists |
| **Startup Rehydration** | ❌ NONE | Ephemeral - not persisted |
| **Event Publishers** | `PermissionService`, `UIController` | Publish `PERMISSION_CHECK_REQUEST`, `PERMISSION_CHECK_RESULT` |
| **Reducer Consumer** | `_reduce_permission_snapshot` | `core/app_state.py:2028` |
| **Persistence Path** | ❌ NONE | In-memory only |
| **Recovery Path** | ❌ N/A | Intentionally ephemeral |
| **Snapshot Authoritative?** | ❌ NO | In-memory only |
| **Projection Only?** | ✅ YES | Ephemeral projection |
| **Constitutional Risk** | ✅ LOW | Intentionally transient |

**Note:** Permission checks are ephemeral by design - no persistent audit trail required per spec.

---

## Summary Matrix

| Snapshot | Repository | Startup Hydration | Persistence | Idempotent | Constitutional Risk |
|----------|------------|-------------------|-------------|------------|---------------------|
| WorldModelSnapshot | ✅ EntityRepository | ❌ NONE | ✅ | N/A | ⚠️ MEDIUM |
| CapabilityLibrarySnapshot | ✅ RuntimeProviderRepo | ✅ | ✅ | ✅ | ✅ LOW |
| ExecutionLibrarySnapshot | ✅ ExecutionRunRepo | ❌ NONE | ✅ | ✅ | ⚠️ HIGH |
| AgentPipelineSnapshot | ❌ NONE | ❌ NONE | ❌ | N/A | ⚠️ HIGH |
| ProviderRegistrySnapshot | ✅ RuntimeProviderRepo | ✅ | ✅ | ✅ | ✅ LOW |
| WorkflowLibrarySnapshot | ✅ WorkflowRunRepo | ✅ | ✅ | ❌ BUG | ⚠️ MEDIUM |
| PermissionCheckSnapshot | ❌ NONE | ❌ NONE | ❌ | N/A | ✅ LOW |

---

## Confirmed Defects

### DEFECT 1: WorldModelSnapshot Startup Rehydration
- **Severity:** MEDIUM
- **Impact:** World model shows empty on startup, even with persisted entities
- **Root Cause:** `WORLD_MODEL_GRAPH_REFRESHED` topic never published
- **Fix Required:** Add startup publisher in EntityService or WorldModelBusHandler

### DEFECT 2: ExecutionLibrarySnapshot Startup Rehydration  
- **Severity:** HIGH
- **Impact:** Execution run history lost on restart
- **Root Cause:** `ExecutionRunService._on_load()` missing `_publish_recent_runs()` call
- **Fix Required:** Add rehydration publish similar to `WorkflowPersistenceService`

### DEFECT 3: WorkflowLibrarySnapshot total_started Idempotency
- **Severity:** MEDIUM
- **Impact:** Counter increments on every WORKFLOW_STARTED, even duplicates
- **Root Cause:** Line 2173 always increments `total_started`
- **Fix Required:** Only increment when run is genuinely new

---

## Disproven Claims

The following claims from Audit B were **DISPROVEN**:

| Claim | Status | Evidence |
|-------|--------|----------|
| "Snapshot could become authoritative over repository" | ❌ DISPROVEN | All snapshots are properly marked as projections |
| "Workflow_RUNS_LOADED double count" | ❌ DISPROVEN | `_reduce_workflow_runs_loaded` handles deduplication |
| "Repository ownership concerns" | ❌ DISPROVEN | Repositories properly own persistence |

---

## Required Actions

### Priority 1 (Critical)
1. Fix DEFECT 1: Add WorldModelSnapshot startup rehydration
2. Fix DEFECT 2: Add ExecutionLibrarySnapshot startup rehydration

### Priority 2 (High)
3. Fix DEFECT 3: Repair WorkflowLibrarySnapshot total_started idempotency

### Priority 3 (Medium)
4. Add performance tests for event throughput
5. Document ephemeral vs persistent snapshot contracts

---

**Report Generated:** 2026-07-13  
**Next Review:** After defect remediation
