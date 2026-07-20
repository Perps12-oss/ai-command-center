# Phase 5: Async EventBus Policy Implementation

**Status:** PARTIAL (code-verified 2026-07-20 — not COMPLETE)  
**Priority:** HIGH  
**Estimated Effort:** 2-3 weeks  
**Dependencies:** Phase 1-4 complete ✅  
**Authority:** `ASYNC_EVENTBUS_POLICY.md`, `PROJECT_CONSTITUTION_V4.md`  
**Verification:** `docs/audits/PHASE_PLANS_ARCHIVE_VERIFICATION.md` — keep in `docs/plans/` until exit criteria met on `main`

---

## Executive Summary

Implement non-blocking dispatch for heavy EventBus handlers while maintaining backward compatibility with synchronous handlers. The goal is to reduce UI latency and improve throughput for workflow/orchestration operations.

---

## Current State

**Design:** Complete in `ASYNC_EVENTBUS_POLICY.md`

**Implementation:** Sync dispatch active; async components stubbed

---

## Architecture

### Dispatch Tiers

| Tier | Name | Handlers | Mode | Latency Target |
|------|------|----------|------|----------------|
| R4a | Immediate | UI updates, state changes | Sync | <5ms |
| R4b | Queued | Tool execution | Queue (1 worker) | <50ms |
| R4c | ThreadPool | Workflow, orchestration | ThreadPool | <200ms |
| R4d | Dedicated | Model calls | Queue (dedicated) | <500ms |

### Class Diagram

```text
DispatchPolicy (ABC)
├── SyncDispatchPolicy      (default, backward compat)
├── TieredDispatchPolicy    (new implementation)
└── AsyncDispatchPolicy     (future migration target)

EventBus
├── _dispatch(topic, event) → uses current policy
├── dispatch_async(topic, event) → always async
└── dispatch_sync(topic, event) → always sync
```

---

## Implementation

### 5.1 Dispatch Policy Base

**File:** `ai_command_center/core/events/dispatch_policy.py`

```python
class DispatchPolicy(ABC):
    @abstractmethod
    def dispatch(self, handler: Callable, event: Event) -> None: ...
    
    def supports_async(self) -> bool:
        return False
```

### 5.2 Tiered Dispatch Implementation

**File:** `ai_command_center/core/events/tiered_dispatch_policy.py`

**Tier classification:**
- UI handlers: `ui.*`, `app.*`
- Tool handlers: `tool.*`
- Workflow handlers: `workflow.*`
- Orchestration handlers: `orchestration.*`
- Model handlers: `llm.*`, `model.*`

### 5.3 Worker Pool

**File:** `ai_command_center/core/events/async_dispatch_queue.py`

- Queue-based for R4b/R4d
- ThreadPool for R4c
- Graceful shutdown with timeout

### 5.4 Configuration

**File:** `ucgs.profiles/ai-command-center.yaml`

```yaml
dispatch_policy:
  tiered: true
  pools:
    tool_execution:
      workers: 1
      queue_size: 100
    workflow:
      workers: 4
      queue_size: 50
    model:
      workers: 2
      queue_size: 10
```

---

## Migration Guide

### For Service Authors

**Before (implicit sync):**
```python
def _on_tool_complete(self, event: Event) -> None:
    # This was sync
    self._update_state(event.payload)
```

**After (explicit tier):**
```python
TIER = DispatchTier.R4B_TOOL  # or config-driven

def _on_tool_complete(self, event: Event) -> None:
    self._update_state(event.payload)
```

### Backward Compatibility

- Default policy remains `SyncDispatchPolicy` until explicit opt-in
- Feature flag: `ASYNC_DISPATCH_ENABLED`
- Gradual migration: Tier by tier, starting with R4b

---

## Testing

### Unit Tests

- [ ] `test_sync_dispatch_policy` — existing behavior preserved
- [ ] `test_tiered_dispatch_classification`
- [ ] `test_async_dispatch_queue`
- [ ] `test_worker_pool_shutdown`

### Integration Tests

- [ ] `test_concurrent_tool_execution`
- [ ] `test_workflow_dispatch_latency`
- [ ] `test_model_queue_isolation`

### Performance Benchmarks

- [ ] Baseline: current sync latency
- [ ] Target: 95th percentile < 50ms for R4a
- [ ] Regression threshold: +10ms acceptable

---

## Exit Criteria

- [ ] All existing tests pass (471 tests)
- [ ] New async tests pass
- [ ] Architecture lint clean
- [ ] UCGS PASS
- [ ] Performance benchmarks within target
- [ ] Migration guide complete

---

## Files

### Create

```
ai_command_center/core/events/dispatch_policy.py
ai_command_center/core/events/tiered_dispatch_policy.py
ai_command_center/core/events/async_dispatch_queue.py
tests/test_tiered_dispatch_policy.py
tests/test_async_dispatch_queue.py
```

### Modify

```
ai_command_center/core/event_bus.py
ucgs.profiles/ai-command-center.yaml
docs/architecture/ASYNC_EVENTBUS_POLICY.md (update implementation status)
```

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial plan |
