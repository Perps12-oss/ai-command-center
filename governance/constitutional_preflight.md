# CONSTITUTIONAL PRE-FLIGHT

Task Description:
Stop EventBus/UI freezes when background publishers (Ollama health,
system monitor) invoke UIQueue.enqueue. `event_generate` was called from
non-Tk threads, blocking handlers for seconds (ollama.status ~6s,
system.snapshot ~865ms). Make UIQueue wake Tk only from the UI thread;
shorten Ollama health HTTP timeouts; skip unchanged status publishes;
include handler names in budget logs for actionable observability.
No new topics, services, or schema changes.

Files Reviewed:
- PROJECT_CONSTITUTION_V4.md
- AGENTS.md
- docs/ARCHITECTURE.md
- docs/architecture/ASYNC_EVENTBUS_POLICY.md
- ai_command_center/ui/ui_queue.py
- ai_command_center/ui/shell/event_coordinator.py
- ai_command_center/services/ollama_http_service.py
- ai_command_center/core/event_bus.py
- ai_command_center/core/events/dispatch_policy.py
- governance/constitutional_preflight.md

Authorities Reviewed:
- Level 1: PROJECT_CONSTITUTION_V4.md
- Level 2: AGENTS.md, docs/ARCHITECTURE_ENFORCEMENT.md
- Level 3: docs/ARCHITECTURE.md, docs/architecture/ASYNC_EVENTBUS_POLICY.md

Protected Assets Impacted:
- EventBus (Tier A) — observability log fields only; dispatch semantics unchanged
- UI shell — UIQueue wake path + lighter ollama.status UI projection
- OllamaHttpService — health-check timeout / publish coalescing only

Sources of Truth Impacted:
- None. AppState remains SoT; UI still projects via UIQueue on the Tk thread.

Architectural Invariants Impacted:
- Invariant 1: Ownership Flow preserved
- Invariant 2: UI Isolation — strengthens Tk main-thread affinity
- ASYNC_EVENTBUS_POLICY UIQueue invariant: handlers may enqueue; only Tk thread mutates widgets

Contracts Impacted:
- UIQueue.enqueue: thread-safe put; Tk wake only on UI thread (fallback poll drains)
- OLLAMA_STATUS publish cadence: skip when online/detail unchanged
- Budget warning log includes handler qualname

Gate Impact Assessment:
- No gate removals
- Adds/extends UIQueue + ollama health tests
- Existing constitution / UCGS / pytest remain in force

Historical Gates Impacted:
- python3 -m pytest
- python3 -m ruff check ai_command_center
- scripts/verify_constitution.py
- tools/ucgs_runner.py + ucgs_ci_gate.py

Regression Risk:
Medium-low. Background UI updates may wait up to the poll interval (≤50ms)
instead of virtual-event wake; chat streaming already budgets for ~50ms
UI_STREAM_INTERVAL_MS. Eliminates cross-thread Tk hangs.

Constitutional Status:

APPROVED
