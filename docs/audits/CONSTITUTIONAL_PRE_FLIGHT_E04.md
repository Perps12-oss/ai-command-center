# Constitutional Pre-Flight — PR-UI-E04 Navigation Shell

**Slice:** PR-UI-E04 — Navigation Shell  
**Roadmap:** `docs/architecture/UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md`  
**Baseline:** `origin/main` only  

---

## Authority checks

- [x] `PROJECT_CONSTITUTION_V4.md` — Article 0 (Supremacy) acknowledged.
- [x] `docs/UI_CONSTITUTION.md` — Article 9 (Navigation exists to expose operational domains; Command Center mandatory primary workspace), Article 21 (UI reads AppState / renders state / publishes events only).
- [x] `docs/agents/DEVIN_UI_HANDOVER.md` — one evolution slice per PR; branch from `origin/main`.
- [x] `docs/agents/CURSOR_AUDIT_GATE.md` — scope, primitive reuse, no new graph/timeline/inspector engine.

---

## Scope

PR-UI-E04 only:

1. Make `Sidebar` groups collapsible (Ops / Monitor / Library / Settings).
2. Finalize `command_center` as the unconditional default view.
3. Update `KeyboardShortcutsOverlay` to document navigation shortcuts.
4. Update `docs/architecture/ACC_UI_REFURBISHMENT.md` navigation design note.

No E05–E13 work. No new graph/timeline/inspector engine. No backend service or repository calls from UI.

---

## Contracts

- `ui/components/sidebar.py` — `Sidebar` exposes `set_active(view_id)` and `toggle_collapse()` unchanged; adds group toggles.
- `ui/shell/view_manager.py` — `VIEW_IDS` reordering; remove residual `home` route redirect.
- `ui/components/keyboard_shortcuts_overlay.py` — `SHORTCUTS` list extended with Navigation category.
- `docs/architecture/ACC_UI_REFURBISHMENT.md` — design note appended.

---

## AppState

- Fields added: **none**.
- Composition-only: **yes**. Sidebar state (active view, group collapse) is UI-local chrome, not AppState.

---

## Risks / deferrals

- Collapse state is not persisted across sessions (UI chrome only). Persistence deferred to settings work if requested.
- Keyboard shortcut overlay descriptions are static strings; dynamic binding inspection deferred.

---

## Pre-flight verdict

Proceed with implementation.
