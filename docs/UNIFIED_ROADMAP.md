# Unified Roadmap — AI Command Center

This roadmap consolidates the three previously separate plans (Workspace OS walking skeleton, Stage 2 UX roadmap, and the AGENTS.md architecture refactor) into one ordered, track-based plan where each completed sub-category unlocks the next.

---

## Supremacy

`PROJECT_CONSTITUTION_V4.md` > `AGENTS.md` > `ARCHITECTURE_DIAGRAM.md` > this roadmap. No implementation may weaken a constitutional guarantee.

---

## Guiding principle

```text
UI → AppState → EventBus → Services → Repositories → Storage
```

UI is a renderer/intent publisher only. All state flows through `AppState` or `SettingsSnapshot`. No direct service-to-service calls, no global state, no repository access from UI.

---

## Mapping of old plans into this roadmap

| Old plan | Where it lives in this roadmap | Current status |
|---|---|---|
| Workspace OS walking skeleton | Track 5, sub-category 5.1 | ✅ Done (base inspector, entity creation, launch, AppState counters) |
| Stage 2 P0 foundation | Track 1, sub-categories 1.1–1.3 | ✅ Mostly done (domain models, repositories, settings layer exist) |
| Stage 2 P1 UX (markdown, tokens, CRUD, views) | Track 4, sub-categories 4.1–4.4 | ✅ Done |
| Stage 2 P2 architecture | Track 2, sub-categories 2.1–2.3; Track 3, sub-categories 3.1–3.3 | ⚠️ Partial (ServiceManager/Bus exist, but lifecycle alignment and AppState projection gaps remain) |
| Stage 2 P2 future platform | Track 6, sub-categories 6.1–6.5 | ⏳ Not started |
| Chat Workspace v1.5 plan | Track 4, sub-category 4.2 | ✅ Mostly done (AppState chat projection, lifecycle hardening) |
| AGENTS.md architecture refactor | Tracks 1–4 | ✅ Mostly satisfied (projection + UI isolation + Workspace OS compliance done) |

---

## Track 1 — Foundation

Goal: canonical data contracts, settings layer, and repository ownership.

| # | Sub-category | Status | Exit criteria |
|---|---|---|---|
| 1.1 | Domain models under `ai_command_center/domain/` | ✅ | All runtime contracts are dataclasses; no plain dicts in services |
| 1.2 | Settings layer (`core/settings/`) | ✅ | Schema validation, migration, snapshot event wired |
| 1.3 | Repository layer (`repositories/` + `core/*_repository.py`) | ✅ | Storage owned only by repositories; ApplicationCore is the sole constructor |
| 1.4 | **Alignment audit** — remove duplicated/inconsistent repository packages | ✅ | `core/settings/settings_repository.py` re-exports canonical SQLite-backed repository; `services/settings_service` publishes `SettingsSnapshot` |

---

## Track 2 — Runtime Engine

Goal: explicit EventBus topics, service lifecycle framework, and tool runtime.

| # | Sub-category | Status | Exit criteria |
|---|---|---|---|
| 2.1 | Document and stabilize canonical EventBus topics | ✅ | All production topics listed, versioned, and wildcard-free outside debug mode |
| 2.2 | Service lifecycle framework (`BaseService` + `ServiceState`) | ✅ | Lifecycle states match AGENTS.md: `STOPPED`, `STARTING`, `READY`, `DEGRADED`, `ERROR`, `STOPPING`; no conflicting `HIBERNATED`/`ACTIVE` usage in published state |
| 2.3 | Tool runtime (`tool_registry.py` + `tool_executor.py`) | ✅ | `ToolRegistry` registers only; `ToolExecutor` executes and cancels; `ToolExecutorService` delegates to it rather than bypassing it |

---

## Track 3 — State & Observability

Goal: complete AppState projection and passive telemetry.

| # | Sub-category | Status | Exit criteria |
|---|---|---|---|
| 3.1 | Telemetry service (`telemetry/telemetry_service.py`) | ✅ | Publishes `TelemetryEvent` to EventBus; no inference at runtime |
| 3.2 | AppState full projection | ✅ | Notes list, memory list, plugin catalog, system snapshot, and Workspace OS entity list all projectable from `AppStateStore.snapshot` |
| 3.3 | `SystemSnapshot` + `SettingsSnapshot` audit | ✅ | Domain contracts exist; ensure every consumer reads via `AppState` |

---

## Track 4 — UI Contract Compliance

Goal: every view reads from `AppState`/`EventBus` and writes only through `UIController`/`EventBus`.

| # | Sub-category | Status | Exit criteria |
|---|---|---|---|
| 4.1 | UI isolation audit across `ai_command_center/ui/` | ✅ | No direct file writes, SQLite access, service calls, or tool invocation from views |
| 4.2 | Chat Workspace v1.5 compliance | ✅ | Chat renders from AppState + chat events; stale-request guards in place |
| 4.3 | Memory / Notes / Plugins / System views compliance | ✅ | Views read lists from AppState projection; event handlers only mutate via EventBus |
| 4.4 | Workspace OS UI compliance | ✅ | Inspector reads full entity list from AppState, not directly from `WorkspaceOsService` |

---

## Track 5 — Feature Completion

Goal: user-visible workflows are polished and end-to-end.

| # | Sub-category | Status | Exit criteria |
|---|---|---|---|
| 5.1 | Workspace OS walking skeleton | ✅ | Inspector, creation, search, launch, AppState counters |
| 5.2 | Chat markdown + token standardization | ✅ | `markdown_view.py`, `theme_v2` radius tokens, code blocks/bold/italic |
| 5.3 | Memory / Notes / Plugins / System refinements | ✅ | Add memory, note preview/creation, plugin status/restart, process table |
| 5.4 | Command palette integration for Workspace OS | ✅ | Workspace OS entities searchable and launchable from `Ctrl+K` palette |
| 5.5 | Settings and overlay polish | ✅ | Theme/alpha round-trip, compact/palette modes, tray fallback |

---

## Track 6 — Platform Scale

Goal: reusable component library and future extensibility.

| # | Sub-category | Status | Exit criteria |
|---|---|---|---|
| 6.1 | Component library gallery | ✅ | `ComponentGalleryView` accessible from palette; documents tokens and components |
| 6.2 | Design-system tokens fully applied | ✅ | No hard-coded fonts in audited views; Workspace OS inspector uses `theme_v2` |
| 6.3 | Plugin framework v2 | ⏳ | Dynamic enable/disable with restart, extension isolation |
| 6.4 | Vector search / memory graph enhancements | ⏳ | Embeddings-based memory retrieval |
| 6.5 | Multi-agent runtime | ⏳ | Agent spawning beyond single chat |

---

## Current position

- **Tracks 1–3 and 4–5 are complete.** Foundation, runtime engine, state/observability, UI contract, and visible features are all implemented.
- **Track 6.3–6.5 remain future work.** Plugin framework v2, vector search, and multi-agent runtime are not started.

---

## Recommended next sub-category

**Track 6.3 → Track 6.4 → Track 6.5**

1. **Plugin framework v2** (Track 6.3): dynamic enable/disable with restart, extension isolation.
2. **Vector search / memory graph enhancements** (Track 6.4): embeddings-based memory retrieval.
3. **Multi-agent runtime** (Track 6.5): agent spawning beyond single chat.

After that, the architecture is unified and the platform scale layer is complete.

---

## Definition of done for a sub-category

- All code touched by the sub-category passes `py_compile`.
- `python -m unittest discover tests` passes.
- `scripts/verify_constitution.py` passes.
- `scripts/verify_contracts.py` passes.
- Phase-specific verify scripts pass (e.g., `verify_phase2.py`, `verify_phase5c.py`, `verify_capability_completion.py`).
- No regressions to previously completed sub-categories.

---

## How to use this roadmap

1. Pick the next sub-category from the recommended path.
2. Produce a constitutional pre-flight before implementation (per `AGENTS.md`).
3. Implement only that sub-category; keep changes minimal and additive.
4. Run the verification gates above.
5. Update the status (✅ / ⚠️ / ⏳) in this file and commit.
6. Move to the next sub-category only after the current one is verified.

---

## Residual risks

- **Dual repository paths:** `core/settings/settings_repository.py` vs `db/repository.py` / `repositories/settings_repository.py` may confuse future contributors.
- **Lifecycle state mismatch:** `ServiceState` has both AGENTS.md-required states and legacy `HIBERNATED`/`ACTIVE` aliases that must be reconciled.
- **UI direct event subscriptions:** `app.py` subscribes to many EventBus topics directly; as AppState projection grows, these should be replaced by `AppState` subscriptions.
- **ToolExecutor stub:** `ai_command_center/tools/tool_executor.py` does not actually run tools; execution currently happens inside `ToolExecutorService`.
