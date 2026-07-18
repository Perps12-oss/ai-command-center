# Placeholder Audit — Phase 11 Remediation

Audit date: 2026-07-18  
Scope: `ai_command_center/ui` Phase 11 workspaces + related shells  
Policy: implement, remove, or justify every `TODO` / `FIXME` / `STUB` / `PLACEHOLDER` / “coming soon”

---

## Summary

| Category | Count | Disposition |
|---|---:|---|
| Prohibited markers in Phase 11 workspace trees | 0 | Clean (verifier-enforced) |
| CTk `placeholder_text=` entry hints | N (widget API) | **Justified** — CustomTkinter entry hint API, not unfinished work |
| Orphan gallery view | 1 | **Removed** (`component_gallery_view.py`) |
| Inspector empty-selection copy | 1 | **Renamed** — `_EMPTY_SELECTION_HINT` (was `_DEFAULT_PLACEHOLDER`) |

---

## Findings

### Removed

| Item | Action |
|---|---|
| `ai_command_center/ui/views/component_gallery_view.py` | Deleted. Unregistered orphan (absent from `VIEW_IDS` / sidebar). Design-system catalog is not a Phase 11 operator workspace. |

### Renamed / clarified (not incomplete work)

| Item | Action |
|---|---|
| `inspector_host.py` `_DEFAULT_PLACEHOLDER` / `_show_placeholder` | Renamed to `_EMPTY_SELECTION_HINT` / `_show_empty_hint`. Real empty-selection UX, not a stub. |

### Justified intentional abstractions

| Item | Justification |
|---|---|
| `placeholder_text=` on CTkEntry widgets (search boxes, command box, dialogs) | CustomTkinter API for input hints. Not TODO/stub markers. Verifier uses word-boundary `PLACEHOLDER` and does not flag `placeholder_text`. |
| World Model custom `tk.Canvas` graph | GraphCanvas remediation tracked separately; **out of scope** for this remediation sprint. |

### Verifier enforcement

`scripts/verify_ui_constitution.py` `_check_no_placeholders` now scans **all Phase 11A–11F workspace files** (+ `surface_state.py`) and fails on:

- `TODO`, `FIXME`, `COMING_SOON`, `PLACEHOLDER`, `TEMP`, `MOCK`, `DUMMY`, `STUB`
- case-insensitive `coming soon`
- surviving `PlaceholderView`
- surviving `component_gallery_view.py`

---

## Residual (explicitly accepted)

1. **GraphCanvas reuse** — tracked outside this remediation; do not modify graph architecture here.
2. Bandit baseline may still list the deleted gallery path until the next baseline refresh (harmless unused key).
