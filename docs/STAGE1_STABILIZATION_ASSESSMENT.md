# Stage 1 Stabilization Assessment

Status: assessment only — no code changes requested.

Scope: post-unification review of the canonical `main` branch after merging `feature/workspace-ui-unification`.

---

## 1. Architecture health assessment

### Overall: B+

The Stage 1 unification successfully enforced the core ownership boundary:

```text
UI -> AppState -> EventBus -> Services -> Repositories -> Storage
```

No UI module directly accesses SQLite, settings files, Ollama, or the filesystem. State flows through `AppState` and `SettingsSnapshot`.

### Strengths

| Area | Finding |
|---|---|
| EventBus wiring | All views receive updates via `UIController` and `UIQueue` only. |
| Repository isolation | `conversation_repository`, `notes_repository`, `memory_repository`, `settings_repository`, `telemetry_repository` own persistence. |
| Domain contracts | `SettingsSnapshot`, `SystemSnapshot`, `ContextBundle`, and other dataclasses are used instead of raw dicts. |
| Service lifecycle | `BaseService` defines `STOPPED/STARTING/READY/DEGRADED/ERROR/STOPPING` states and publishes `service.state_changed`. |
| Tool runtime | `ToolRegistry` and `ToolExecutor` exist with clear separation of registration vs execution. |
| Theme system | Tokens and theme manager are centralized; alpha slider is wired through `settings.set_request`. |

### Weaknesses

| Area | Finding | Risk |
|---|---|---|
| Circular imports | `services/__init__.py` was loading all services, causing a circular import with `core/service_manager.py`. A hotfix reduced it to `BaseService` + `ServiceState`. The underlying package-level coupling remains a trap. | Medium — any future attempt to re-export services will reintroduce the cycle. |
| Service manager coupling | `ServiceManager` still lives in `core/` and imports `ServiceState` from `services/`. This is a cross-package dependency that should be owned by `core` or `services`, not split. | Low — currently works, but blurs the boundary. |
| Settings projection drift | `AppState` has `settings` (a `SettingsSnapshot`) but also duplicated fields like `model_name`, `provider`, `vault_path` in `SettingsSnapshot`. Some fields are aliases, some are stale. | Medium — risk of `settings.theme` vs `settings.accent` vs theme-manager state diverging. |
| `ollama_online` placement | The UI expected `AppState.ollama_online`; the real field is `AppState.system_snapshot.ollama_online`. A hotfix patched the UI, but the mismatch shows the domain model is not fully internalized. | Low — fixed, but indicates spec drift. |

### Architecture health score: 7/10

---

## 2. UX debt list

| # | Debt | Severity | Notes |
|---|---|---|---|
| 1 | Settings view reloads on every state change | High | Fixed during stabilization, but the pattern of reloading the entire editor view from `AppState` on every event is fragile. Views that hold interactive controls should not be overwritten while the user is editing them. |
| 2 | No focus management / keyboard shortcuts in settings | Medium | Tab order, Enter-to-save, and Escape-to-cancel are not implemented. |
| 3 | Theme swatches do not preview hover/selection state | Low | Swatches have an active ring, but no hover feedback or tooltip. |
| 4 | Opacity slider value can be overwritten by theme selection | Medium | Selecting a theme resets the slider to the theme's `alpha`. This is surprising if the user intentionally set a custom opacity. |
| 5 | Chat input placeholder is static | Low | No dynamic hint based on context (e.g., when a note is selected). |
| 6 | Toast durations are not configurable | Low | All toasts use the same timeout. |
| 7 | No empty-state illustrations | Low | Empty lists use plain text labels. |
| 8 | System view process list is not sortable or filterable | Medium | Users cannot search or kill processes. |
| 9 | Memory view has no pagination | Medium | All memories are rendered at once; large vaults will hurt performance. |
| 10 | Notes view does not show selected note content | Medium | Only title, path, and snippet are shown; no inline preview. |

---

## 3. Technical debt list

| # | Debt | Severity | Notes |
|---|---|---|---|
| 1 | Async task cleanup in `OllamaHttpService` | High | `_health_check()` coroutine is not cancelled on unload; `verify_capability_completion.py` and manual shutdown print `Task was destroyed but it is pending!`. |
| 2 | `run_daily_driver.py` requires live Ollama | High | The gate is environmental and cannot run in CI or on machines without a running Ollama server. |
| 3 | `_Sparkline._draw` overrides `CTkFrame._draw` | Medium | Fixed by accepting `no_color_updates`, but inheriting from `CTkFrame` and overriding its internal `_draw` method is fragile. A plain `ctk.CTkFrame` containing a `CTkCanvas` would be cleaner. |
| 4 | `SettingsView` mixes presentation and save logic | Medium | The view calls `_on_save` directly from widget callbacks. A small presenter/controller layer would make testing easier. |
| 5 | `ChatView` owns in-memory session history | Medium | `_sessions` dict is stored in the view, not in `AppState` or a session service. This creates duplication with `SessionService`. |
| 6 | `HomeView` rebuilds activity feed rows on every event | Low | `_build_rows()` destroys and recreates widgets; acceptable for small feeds but not scalable. |
| 7 | Hard-coded colors and fonts in views | Low | `plugins_view.py` uses `ctk.CTkFont(size=18, weight="bold")`. `chat_view.py` defines `_CLR_*` constants inline. These should be tokenized. |
| 8 | `PlaceholderView` still exists for unknown views | Low | No real unknown views exist; it is dead code. |
| 9 | `settings_view.py` uses `str(value)` for booleans | Low | `low_memory_mode` is serialized as `"true"`/`"false"` strings rather than a typed boolean. |
| 10 | `ui/tray.py` uses `pathlib.Path` directly | Low | Acceptable for tray icon asset loading, but should be documented as a platform edge. |

---

## 4. Remaining UI inconsistencies

| View | Inconsistency |
|---|---|
| **Plugins** | Uses `ctk.CTkFont(size=18, weight="bold")` instead of `T.FONT_TITLE`. No `GlassCard` wrapper; flat background unlike other views. |
| **Notes** | Uses `T.FONT_TITLE` but the header is not wrapped in a consistent header frame. Search instructions are static text instead of an inline hint. |
| **System** | `CTkCanvas` uses `bg=T.BG_DEEP` parameter (tkinter style) while other views use `fg_color`. Sparkline fill uses `stipple="gray25"` which may behave differently on dark mode. |
| **Chat** | Internal `_InputPill` has its own focus management; the main `ChatView` did not expose `focus_input()` until a hotfix. Bubble margins and wrap lengths are hard-coded. |
| **Memory** | Delete button is a trash emoji on a transparent button; no confirmation dialog. |
| **Settings** | `GlassCard` is used inside a scrollable frame, but the connection section uses a second `GlassCard` without a consistent section header style. |

### Global inconsistencies

- **Corner radius**: `T.CORNER_RADIUS` is used in some places, literal `8` in others.
- **Font sizes**: `T.FONT_TITLE`, `T.FONT_HEADER`, `T.FONT_BODY`, `T.FONT_SMALL` are used, but some labels still use `ctk.CTkFont(...)` directly.
- **Spacing**: `T.PAD` is used, but some internal frames use magic numbers like `12`, `16`, `10`.
- **Card containers**: Home/Chat/Notes use `GlassCard`; Plugins does not; Memory uses both header and card inconsistently.

---

## 5. Remaining legacy CTk artifacts

| Artifact | Location | Recommendation |
|---|---|---|
| `CTkCanvas(bg=...)` | `system_view.py` | Use `CTkFrame` + `CTkCanvas` wrapper; remove tkinter-style `bg` parameter. |
| `ctk.CTkFont(size=18, weight="bold")` | `plugins_view.py` | Replace with `T.FONT_TITLE`. |
| Inline `_CLR_*` hex colors | `chat_view.py` | Promote to `theme_v2.py` semantic color tokens. |
| Hard-coded emoji icons | `home_view.py`, `memory_view.py`, `notes_view.py` | Optional: replace with Lucide-style icons if the project ever adopts an icon library; currently acceptable. |
| `stipple="gray25"` | `system_view.py` | Platform-dependent X11/Win32 canvas behavior; may not render consistently. |
| `corner_radius=8` literals | multiple views | Standardize on `T.CORNER_RADIUS` or `T.CARD_RADIUS`. |
| `placeholder_text` in entries | multiple views | Acceptable; not legacy. |

---

## 6. Potential regressions introduced during Stage 1

| Regression | Status | Evidence |
|---|---|---|
| `AppState.ollama_online` missing | **Fixed** | Crash on startup; patched to `system_snapshot.ollama_online`. |
| `ChatView.focus_input()` missing | **Fixed** | Sidebar navigation to chat crashed; method added. |
| `_Sparkline` CTkFrame `_draw` signature mismatch | **Fixed** | System view crashed on open; `_draw` now accepts `no_color_updates`. |
| Settings opacity slider reset while dragging | **Fixed** | Moved `load_from_snapshot` out of `_apply_state` into `_show_view`. |
| `services/__init__.py` circular import | **Fixed** | Reduced to `BaseService` + `ServiceState`. |
| `verify_phase3b.py` literal token check | **Fixed** | Script now checks `CHAT_CHUNK`/`CHAT_CANCELLED` constants. |
| `ChatHandlerService` not using `ObsidianService.get_context_notes()` | **Fixed** | Direct call added; passes Phase 3C. |

### Residual risks

| Risk | Likelihood | Impact |
|---|---|---|
| Other `AppState` attribute mismatches | Medium | Low | More UI code may assume fields that were moved to nested snapshots. |
| Theme/token renames break components | Low | Medium | `theme_v2.py` is new; some views still reference old OneDrive aliases. |
| Async task leaks in services | High | Low | Not user-visible but pollutes logs and may delay shutdown. |
| `load_from_snapshot` pattern in other views | Medium | Low | Similar reset issues could exist in `MemoryView` or `NotesView` if they gain interactive editors. |

---

## 7. `verify_phase5c.py` investigation

### Current behavior

Running `scripts/verify_phase5c.py` executes `scripts/verify_phase5c_preflight.py`, which runs a list of gates:

```text
verify_contracts.py
verify_phase3d.py
verify_phase4a.py
verify_phase4b.py
verify_phase4c.py
verify_phase4d_compression.py
verify_phase4e.py
verify_phase4f.py
verify_phase5a.py
verify_phase5b.py
audit_note_integration.py
run_daily_driver.py
```

### Result

All Phase 4 scripts and Phase 5A/5B gates **pass**. The only failure is `run_daily_driver.py`.

### Root cause of the failure

`run_daily_driver.py` is a live-Ollama integration test. It:

1. Wires the full service stack including `OllamaHttpService`.
2. Publishes `ui.command` with clipboard text and expects `chat.complete` within 90 seconds.
3. Reconfigures `ollama_url` to `http://127.0.0.1:1` and expects `chat.error`.
4. Restores `ollama_url` to `http://127.0.0.1:11434` and expects a successful retry.

The observed failure is:

```text
Exception ignored while closing generator <coroutine object OllamaHttpService._health_check ...>
RuntimeError: coroutine ignored GeneratorExit
Task was destroyed but it is pending!
```

This is a **resource-cleanup error**, not a logic error. The Ollama HTTP service's background health-check coroutine is not properly cancelled during service unload, and the asyncio event loop is torn down while tasks are still pending.

### Whether missing Phase 4 scripts are expected

No scripts are missing. All Phase 4 gates (`4a` through `4f`) are present and pass.

### Whether the gate is obsolete

`verify_phase5c.py` itself is **not obsolete** — it is a useful preflight for the manual stress test described in `docs/PHASE5C_STRESS_TEST.md`. However, `run_daily_driver.py` as a mandatory preflight step is **problematic** because it requires a live Ollama instance.

### Whether the gate should be rewritten

**Recommendation:** split the preflight into two lists:

1. **Automated preflight** (CI-safe): contracts, Phase 3, Phase 4, Phase 5A, Phase 5B, audit.
2. **Integration preflight** (manual/environmental): `run_daily_driver.py` and any live Ollama tests.

`verify_phase5c_preflight.py` should either:

- Skip `run_daily_driver.py` unless `--with-live-ollama` is passed, or
- Mark `run_daily_driver.py` as an optional gate rather than a hard failure.

### Whether missing artifacts should exist

No artifacts are missing. The live Ollama dependency is the real issue. A separate `run_daily_driver.py` should continue to exist, but its failure should be categorized as an **environmental/integration failure**, not a preflight failure.

### Recommendations

1. Make `run_daily_driver.py` optional in `verify_phase5c_preflight.py`.
2. Fix `OllamaHttpService._on_unload` to cancel the health-check coroutine and wait for the asyncio loop to finish pending tasks before shutting it down.
3. Add a `--skip-live-ollama` flag to `verify_phase5c.py` for CI use.

---

## 8. `verify_capability_completion.py` investigation

### Current behavior

The script prints `PASS: capability_completion — clipboard guard, routing, vault UX, help` but exits with visible asyncio errors.

### Exact failure path

```text
Exception ignored while closing generator <coroutine object OllamaHttpService._health_check ...>
RuntimeError: coroutine ignored GeneratorExit
Task was destroyed but it is pending!
task: <Task pending name='Task-1' coro=<OllamaHttpService._health_check() ...>
task: <Task cancelling name='Task-3' coro=<staggered_race.<locals>.run_one_coro() ...>
```

The failure path is:

1. `create_application()` registers `OllamaHttpService`.
2. `OllamaHttpService._on_load()` starts the asyncio loop and schedules `_health_check()`.
3. The test completes and calls `app.shutdown()`.
4. `OllamaHttpService._on_unload()` cancels the active request and stops the loop.
5. The `_health_check` coroutine is not explicitly cancelled; the loop is stopped while the coroutine is still pending.
6. Python's garbage collector reports the pending task as destroyed.

### Whether the failure is environmental

Partially. The **root cause is architectural** — the service does not cleanly shut down its async resources. The symptom is triggered by every test that starts the service, regardless of whether Ollama is running.

### Whether the failure is Ollama-related

No Ollama call actually fails. The error is about asyncio task cleanup, not an Ollama API error.

### Whether the failure is architectural

Yes. The service lifecycle contract (`load`, `hibernate`, `unload`) is synchronous, but `OllamaHttpService` owns an asyncio loop and a health-check coroutine. There is no mechanism to cancel the coroutine and drain the loop before shutdown.

### Whether the failure indicates a real regression

Not a regression introduced in Stage 1 — it is a pre-existing issue in `OllamaHttpService` that became visible after the unification made the full service stack start during more tests.

### Root-cause analysis

In `ai_command_center/services/ollama_http_service.py`:

```python
async def _health_check(self) -> None:
    while True:
        await asyncio.sleep(30)
        ...
```

The coroutine runs forever. `_on_unload` calls `self.cancel()` and stops the loop, but it does not cancel the `_health_check` task itself. When the loop is destroyed, the pending coroutine raises `GeneratorExit`.

### Recommended fix

1. Store the health-check task handle: `self._health_task = asyncio.run_coroutine_threadsafe(self._health_check(), self._loop)`.
2. In `_on_unload`, cancel the task and await its cancellation.
3. Drain the loop with a short timeout before stopping it.

---

## 9. Workspace OS UX review

### 9.1 HomeView

**Strengths**

- Clear dashboard layout: hero banner, status pills, stats strip, quick actions, activity feed.
- Live status pills (Ollama, Vault, Memory) give immediate system health.
- Quick-action cards surface the most common commands.
- Activity feed is human-readable and time-stamped.

**Weaknesses**

- Quick-action cards are not clickable; they only display hints. Users must type commands manually.
- Activity feed is capped at 5 items with no history page.
- Stats strip does not update in real time for all counters (e.g., notes count requires manual refresh).
- No search or command box in the home view itself.

**UX improvements**

1. Make quick-action cards clickable and publish the corresponding command.
2. Add a "Recent commands" section below quick actions.
3. Add a small command box at the top of the home view for one-off queries.
4. Increase activity feed capacity or add a "Show more" link.

**Command-center alignment score: 8/10**

---

### 9.2 ChatView

**Strengths**

- Clean Replit-style bubble UI.
- Supports user, assistant, system, and tool bubbles.
- History panel on the left.
- Context bar shows sources and token estimate.
- Copy button and regenerate button on assistant bubbles.
- Streaming chunks handled correctly.

**Weaknesses**

- The history panel is narrow and may truncate long session names.
- No obvious indicator of which model is currently selected in the chat header.
- Cancel button is only visible while streaming; users may not know it exists.
- No markdown rendering — only plain text with a helper.
- No syntax highlighting for code blocks.
- Context bar text can be long and wrap awkwardly.

**UX improvements**

1. Render markdown with syntax highlighting (use a lightweight renderer or a plain-text formatter with code blocks).
2. Show the active model in the session bar.
3. Add a tooltip or hint for the cancel button.
4. Make the history panel resizable.
5. Add a "clear conversation" button.

**Command-center alignment score: 8.5/10**

---

### 9.3 MemoryView

**Strengths**

- Simple search-as-you-type filter.
- Each row shows the memory text and timestamp.
- Delete action is one click.
- Architecture contract is clean (no service/EventBus imports).

**Weaknesses**

- No confirmation on delete; high risk of accidental deletion.
- No add/edit memory UI — users must use the command box.
- No tags, categories, or metadata display.
- Delete button is a raw emoji; no hover tooltip.
- No pagination; large memory sets will be slow.

**UX improvements**

1. Add a confirmation dialog before delete.
2. Add an "Add memory" button with a simple form.
3. Show memory metadata (tags, related notes) if available.
4. Add pagination or virtual scrolling.
5. Use a real delete icon or button with text.

**Command-center alignment score: 6.5/10**

---

### 9.4 SystemView

**Strengths**

- CPU/RAM meters with sparkline history.
- Disk and network I/O tiles.
- Top process list.
- Self-polling keeps data fresh.
- Accepts `SystemSnapshot` events for integration.

**Weaknesses**

- Process list is not interactive (no kill, no sort, no filter).
- Sparklines are small and not labeled with axes.
- No historical persistence beyond the in-memory 60-point buffer.
- No alert or threshold indicator when CPU/RAM is high.
- The view can feel crowded on smaller screens.

**UX improvements**

1. Add sortable columns to the process list.
2. Add a search/filter box for processes.
3. Highlight meters in warning/error color when thresholds are exceeded.
4. Add a "pause polling" button.
5. Make sparklines larger or clickable for a detailed history.

**Command-center alignment score: 7/10**

---

### 9.5 NotesView

**Strengths**

- Shows search results with title, path, and snippet.
- "Use in chat" button wires note selection.
- Selected note is shown in a status label.
- Clear empty-state messaging.

**Weaknesses**

- No inline preview of the full note.
- No ability to create or edit notes from the view.
- Search query must be entered via the command box; the view has no search field.
- Path display is raw and may be long.
- No note count or indexing status.

**UX improvements**

1. Add a search box inside the view.
2. Add an inline preview pane for the selected note.
3. Add a "New note" button.
4. Show vault indexing status (files indexed, last index time).
5. Truncate paths with a tooltip showing the full path.

**Command-center alignment score: 6/10**

---

### 9.6 PluginsView

**Strengths**

- Reads plugin catalog from the EventBus.
- Shows name, kind, description, and topics.
- Core plugins are marked as always enabled.
- Toggle buttons for non-core plugins.

**Weaknesses**

- No visual hierarchy or grouping.
- No icons or status indicators.
- Flat styling inconsistent with other views.
- No indication of what a toggle actually does (no confirmation, no restart required hint).
- No error state if a plugin fails to load.

**UX improvements**

1. Add icons or category badges for plugins.
2. Group core vs extension plugins.
3. Add a restart-required hint if toggled.
4. Show plugin status (enabled, disabled, error).
5. Add a details panel with manifest content.

**Command-center alignment score: 6/10**

---

## 10. Stage 2 roadmap

Priorities:

- **A. UX refinement** — polish the most visible surfaces.
- **B. Stability** — fix async cleanup and harden gates.
- **C. Capability gaps** — add missing CRUD UI and interactions.
- **D. Future platform evolution** — prepare for non-CustomTkinter futures.

### Proposed Stage 2 backlog

| Priority | Epic | Items | Rationale |
|---|---|---|---|
| **P0** | Stability | 1. Cancel `OllamaHttpService._health_check` on unload and drain the asyncio loop.<br>2. Make `run_daily_driver.py` optional in `verify_phase5c_preflight.py`.<br>3. Add a CI-safe mode for all gates that require network. | Unblocks clean shutdown and reliable CI. |
| **P0** | UX hardening | 1. Add confirmation dialog to MemoryView delete.<br>2. Make quick-action cards in HomeView clickable.<br>3. Add a search box to NotesView. | Fixes the most obvious friction points. |
| **P1** | UX refinement | 1. Markdown rendering in ChatView.<br>2. Resizable chat history panel.<br>3. Better empty states and loading indicators.<br>4. Standardize corner radius, fonts, and spacing tokens. | Improves perceived quality. |
| **P1** | Capability gaps | 1. Add memory creation UI.<br>2. Add note creation/editing UI.<br>3. Process sort/filter in SystemView.<br>4. Plugin details/status in PluginsView. | Closes functional gaps. |
| **P2** | Architecture | 1. Move `ServiceManager` ownership into `services/` or fully into `core/` with clear imports.<br>2. Audit `AppState` vs `SystemSnapshot` vs `SettingsSnapshot` for duplicated fields.<br>3. Document the EventBus topic contract in a single markdown file. | Reduces future drift. |
| **P2** | Future platform | 1. Keep CustomTkinter for Stage 2; do not migrate to PySide6/WebView yet.<br>2. Extract a `ui/components/` library with stable public APIs so a future renderer can be swapped.<br>3. Add design-system documentation and a component gallery script. | Preserves option value without scope creep. |

### Recommended Stage 2 order

1. **Stability sprint** (async cleanup, gate fixes).
2. **UX hardening** (delete confirmation, clickable actions, search boxes).
3. **Polish sprint** (markdown, tokens, empty states).
4. **Capability sprint** (CRUD for memory/notes, process tools, plugin details).

### Non-goals for Stage 2

- Do not migrate away from CustomTkinter.
- Do not add new backend services (e.g., vector search, new LLM providers).
- Do not redesign the overall window layout.
- Do not introduce new architectural layers unless required by stability fixes.

---

## Summary

Stage 1 successfully unified the OneDrive architecture with the Replit visual language. The core architecture is healthy, the major views are functional, and the transparency slider is preserved. The remaining work is stabilization, async cleanup, and UX refinement. The highest-impact next steps are:

1. Fix `OllamaHttpService` async task cleanup.
2. Make live-Ollama gates optional.
3. Add confirmation/interaction polish to MemoryView, HomeView, and NotesView.
4. Standardize tokens and remove remaining hard-coded CTk artifacts.

---

*Document generated: 2026-06-26*
