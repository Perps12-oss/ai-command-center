# Transformation Audit

**Date:** 2026-07-02  
**Branch:** `transformation-program`  
**Authority:** PROJECT_CONSTITUTION_V4.md → AGENTS.md → ARCHITECTURE_ENFORCEMENT.md → ARCHITECTURE.md

This audit captures evidence-based findings across governance, architecture, technical debt, runtime risk, security, and product alignment. Line references reflect the tree at audit time.

---

## 1. Governance Audit

| Check | Status | Evidence |
|-------|--------|----------|
| Constitutional supremacy documented | PASS | `PROJECT_CONSTITUTION_V4.md` Art. 0–II |
| Required authority files present | PASS | `scripts/verify_constitution.py` REQUIRED_FILES list |
| UCGS v5 installed | PASS | `tools/ucgs_runner.py`, `ucgs.config.yaml` |
| Enforcement phase | WARN (Phase 1) | `ucgs.config.yaml:7` `enforcement_mode: warn` |
| CI constitution gate | PASS | `.github/workflows/ucgs.yml:27-28` |
| Agent directives | PASS | `AGENTS.md` ownership flow UI→AppState→EventBus→Services→Repositories |
| Pre-flight template | PASS | `governance/constitutional_preflight.md` |

**Findings**

- UCGS profile is `default`, not `ai-command-center`; project-specific layer rules may be under-enforced in CI.
- `verify_constitution.py` checks file presence only — no import-graph or layer violation detection.
- Large transformation commits will trigger UCGS `large_commit` S2 warnings (`max_files: 25`, `max_added_lines: 500`).

---

## 2. Architecture Audit

### Scale

| Metric | Value | Evidence |
|--------|-------|----------|
| Python files | 223 | `Get-ChildItem -Recurse -Filter *.py` |
| Approximate LOC | ~21,914 | line count across `*.py` |
| UI framework | CustomTkinter | `ai_command_center/ui/app.py`, not PyQt |
| pytest files | 6 | `tests/test_*.py` |
| pytest tests | 29 | `pytest --collect-only` |

### Ownership flow compliance

Target (Constitution Invariant 1):

```text
UI → AppState → EventBus → Services → Repositories → Storage
```

| Layer | Status | Notes |
|-------|--------|-------|
| EventBus backbone | PASS | `core/event_bus.py`, `core/events/topics.py` |
| AppState projection | PASS | `core/app_state.py` — reducers only |
| Service factory composition root | PASS | `core/service_factory.py` |
| UI isolation | PARTIAL | Violations in `hero_panel.py`, `layout/compiler.py` |
| No service→service direct calls | MOSTLY PASS | Chat uses EventBus request/result pattern |
| ModelRouterService wired | **FIXED** | Was missing from `service_factory.py`; now registered |

### UI violations (constitutional)

| File | Line | Violation |
|------|------|-----------|
| `ui/components/hero_panel.py` | 9, 21 | `AssetService()` constructed in UI |
| `ui/layout/compiler.py` | 7, 38–54 | `SpatialRepository()` called directly from UI layer |

**Remediation:** Publish `asset.request` / `layout.schema.request` topics; inject read-only snapshots via AppState or bootstrap wiring through composition root.

### Repository duplication

| Canonical | Legacy / duplicate | Risk |
|-----------|-------------------|------|
| `repositories/settings_repository.py` | `core/settings/settings_repository.py` (re-export) | Contributor confusion |
| `repositories/note_repository.py` | `db/note_repository.py` | Dual persistence paths |
| `repositories/memory_repository.py` | `db/memory_repository.py` | Dual persistence paths |

### God classes

| Module | ~LOC | Concern |
|--------|------|---------|
| `ui/app.py` | ~844 | Many bus subscriptions; should migrate to AppState listeners |
| `ui/views/chat_view.py` | ~1077 | Presentation + stream handling; split per CHAT_MODERNIZATION_SPEC |

---

## 3. Technical Debt Audit

| ID | Item | Severity | Evidence |
|----|------|----------|----------|
| TD-01 | F821 undefined `T` in Badge | P0 | `ui/design_system/status.py:86` — **FIXED** |
| TD-02 | F821 undefined `Any` in WorkspaceOsService handlers | P0 | `core/workspace_os_service.py:128+` — **FIXED** |
| TD-03 | ModelRouterService not in factory | P0 | `core/service_factory.py` — **FIXED** |
| TD-04 | SystemView poll thread leak | P0 | `_build()` called `_start_polling()`; `on_hide`/`on_show` not wired in navigation — **FIXED** |
| TD-05 | WorkspaceOsInspector bus→Tk without marshal | P0 | `ui/workspace_os_inspector.py:141-144` — **FIXED** via `after(0)` |
| TD-06 | EventBus swallows handler exceptions | P1 | `core/event_bus.py:160` — **FIXED** → `bus.handler_error` |
| TD-07 | AppState swallows listener exceptions | P1 | `core/app_state.py:767` — **FIXED** → `app.error` |
| TD-08 | `shell=True` subprocess | P2 | `services/tool_executor_service.py:30`, `core/workspace_os_actions.py:85` — **HARDENED** |
| TD-09 | Ruff F401 unused imports | P3 | 43 auto-fixable; 38 fixed via `ruff --fix` |
| TD-10 | `motion_widgets.py` | P3 | Imports valid; no runtime breakage observed — keep |
| TD-11 | Requirements drift | INFO | Audit only — deps not removed without install verification |

---

## 4. Runtime Risk Audit

| Risk | Impact | Evidence | Mitigation |
|------|--------|----------|------------|
| Background poll threads after view hide | CPU leak, Tk errors | SystemView `_poll` spawned threads every 2s regardless of visibility | Wire `on_show`/`on_hide`; guard `_poll_in_flight` |
| Bus handler updates Tk off main thread | Intermittent UI corruption | WorkspaceOsInspector `_refresh()` from bus thread | `_schedule_refresh()` → `after(0)` |
| Silent subscriber failures | Hidden regressions | EventBus `except: continue` | Publish `bus.handler_error`, log with `logger.exception` |
| Silent AppState listener failures | Stale UI | AppState `except: continue` | Publish `app.error`, log |
| Chat request correlation gaps | Debug difficulty | ChatHandler had no structured logging | `request_id` log on chat start |
| Model routing bypass | Wrong model tier | ModelRouter not registered | Factory registration |

---

## 5. Security Audit

| Area | Finding | Severity |
|------|---------|----------|
| Shell execution | `shell=True` allowed full shell interpretation | HIGH → MEDIUM after shlex split default |
| Metachar fallback | Pipes/redirects still use `shell=True` with warning log | MEDIUM (documented allowlist) |
| Secrets in diff | UCGS forbidden_patterns S4 | LOW on clean tree |
| UI direct repo access | Bypasses permission layer | MEDIUM (architecture violation) |
| Telemetry firewall | Passive runtime, offline analysis only | PASS per ARCHITECTURE.md |
| Wildcard bus subscriptions | Forbidden outside debug_mode | PASS |

---

## 6. Product Alignment Audit

| Dimension | Current state | Target (WORKSPACE_VISION) | Gap |
|-----------|---------------|----------------------------|-----|
| Product identity | Chat-forward command palette | Workspace OS — chat as tool | Vision docs created; UI still chat-centric |
| Workspace OS | Walking skeleton + inspector | First-class workspace canvas | Entity model exists; main UI not workspace-first |
| Agents | Event topics defined (`agent.*`) | Multi-agent runtime | Not implemented — gated |
| Workflows | `core/workflow/workflow.py` stub | Workflow engine | Spec only |
| Plugins | v2 registry + persistence | Extensibility pillar | PASS for v2 scope |
| Model routing | ModelRouterService | Orchestration layer | Wired in factory |
| Cross-platform | Windows-first (hotkey, paths) | Platform strategy doc | macOS/Linux deferred |

---

## Summary Verdict

| Area | Grade | Action |
|------|-------|--------|
| Governance | A- | Advance enforcement roadmap Stage 2 |
| Architecture | B+ | Fix UI violations; dedupe repositories |
| Technical debt | B | P0/P1 items addressed in stabilization pass |
| Runtime risk | B+ | Thread and error surfacing fixed |
| Security | B | Shell hardening; continue allowlist documentation |
| Product alignment | C+ | Vision and roadmap docs define north star |

**Next authority documents:** `WORKSPACE_VISION.md`, architecture specs, `TRANSFORMATION_ROADMAP.md`, `ENFORCEMENT_ROADMAP.md`.
