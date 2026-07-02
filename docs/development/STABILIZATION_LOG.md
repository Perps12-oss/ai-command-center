# Stabilization Log

**Program:** AI Command Center Transformation  
**Date:** 2026-07-02

Each entry documents root cause, constitutional impact, architectural impact, risk, and rollback.

---

## FIX-001: F821 `T` undefined in status.py

| Field | Detail |
|-------|--------|
| **Root cause** | `Badge` used `T.PILL_RADIUS` without importing `theme_v2 as T` |
| **Constitutional impact** | None — UI-only bug |
| **Architectural impact** | Design system consistency |
| **Risk** | Low — import only |
| **Rollback** | Revert import line; use `CORNER_RADIUS` literal |
| **File** | `ai_command_center/ui/design_system/status.py` |

---

## FIX-002: F821 `Any` undefined in workspace_os_service.py

| Field | Detail |
|-------|--------|
| **Root cause** | Event handler type hints used `Any` without import |
| **Constitutional impact** | None |
| **Architectural impact** | Type safety for Workspace OS handlers |
| **Risk** | Low |
| **Rollback** | Revert typing import |
| **File** | `ai_command_center/core/workspace_os_service.py` |

---

## FIX-003: SystemView thread leak

| Field | Detail |
|-------|--------|
| **Root cause** | `_start_polling()` invoked from `_build()` at construct time; navigation never called `on_hide`/`on_show`; overlapping poll threads possible |
| **Constitutional impact** | UI lifecycle hygiene |
| **Architectural impact** | View lifecycle contract: `on_show`/`on_hide` wired from `app.py._show_view` |
| **Risk** | Medium — behavior change: system view idle until shown |
| **Rollback** | Restore `_start_polling()` in `_build()`; remove navigation hooks |
| **Files** | `ui/views/system_view.py`, `ui/app.py` |

---

## FIX-004: WorkspaceOsInspector Tk thread safety

| Field | Detail |
|-------|--------|
| **Root cause** | Bus subscribers called `_refresh()` directly, mutating Tk widgets off main thread |
| **Constitutional impact** | UI isolation — UI updates on main thread only |
| **Architectural impact** | `_schedule_refresh()` → `after(0)` pattern |
| **Risk** | Low |
| **Rollback** | Revert to direct `_refresh()` in subscribers |
| **File** | `ui/workspace_os_inspector.py` |

---

## FIX-005: EventBus handler error surfacing

| Field | Detail |
|-------|--------|
| **Root cause** | `except Exception: continue` swallowed all subscriber failures |
| **Constitutional impact** | Observability of bus contract violations |
| **Architectural impact** | New topic `bus.handler_error`; structured logging |
| **Risk** | Low — recursion guarded by topic check |
| **Rollback** | Restore silent continue |
| **Files** | `core/event_bus.py`, `core/events/topics.py` |

---

## FIX-006: AppState listener error surfacing

| Field | Detail |
|-------|--------|
| **Root cause** | Listener exceptions silently dropped |
| **Constitutional impact** | AppState projection reliability |
| **Architectural impact** | Publishes `app.error` on listener failure |
| **Risk** | Low |
| **Rollback** | Restore silent continue |
| **File** | `core/app_state.py` |

---

## FIX-007: ModelRouterService factory wiring

| Field | Detail |
|-------|--------|
| **Root cause** | Service implemented but not registered in composition root |
| **Constitutional impact** | Incomplete model layer breaks chat routing contract |
| **Architectural impact** | Factory owns all service registration |
| **Risk** | Low — aligns with verify_phase4f expectations |
| **Rollback** | Remove from service_factory registration list |
| **File** | `core/service_factory.py` |

---

## FIX-008: Shell execution hardening

| Field | Detail |
|-------|--------|
| **Root cause** | Unconditional `shell=True` enables injection via metacharacters |
| **Constitutional impact** | Security posture for tool runtime |
| **Architectural impact** | `shlex.split` + `shell=False` default; metachar fallback with warning log |
| **Risk** | Medium — some Windows commands may need shell fallback |
| **Rollback** | Restore `shell=True` only |
| **Files** | `services/tool_executor_service.py`, `core/workspace_os_actions.py` |

---

## FIX-009: Logging foundation

| Field | Detail |
|-------|--------|
| **Root cause** | Key services lacked module loggers and chat correlation |
| **Constitutional impact** | Operational observability |
| **Architectural impact** | `logging.getLogger(__name__)` in EventBus, ChatHandler, ModelRouter |
| **Risk** | Low |
| **Rollback** | Remove logger calls |
| **Files** | `core/event_bus.py`, `services/chat_handler_service.py`, `services/model_router_service.py`, `services/tool_executor_service.py` |

---

## FIX-010: Ruff auto-fix

| Field | Detail |
|-------|--------|
| **Root cause** | 43 unused import / trivial lint issues |
| **Constitutional impact** | None |
| **Architectural impact** | Cleaner imports across 38 files |
| **Risk** | Low — auto-fix only |
| **Rollback** | `git checkout` affected files |

---

## Verification

```bash
python -m compileall ai_command_center
python -m ruff check ai_command_center
python tools/ucgs_runner.py
python -m pytest
```
