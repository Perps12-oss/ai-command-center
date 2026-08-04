# Constitutional Pre-Flight — C1/C2 UI crash + silent-error fixes

**Branch:** `cursor/ui-c1-c2-system-errors-4fb7`  
**Authority:** PROJECT_CONSTITUTION_V4.md

## Intent

1. **C1** — Stop `SystemView` from calling Tk `.after()` on a psutil worker
   thread; route UI hops through `UIQueue` (existing ownership path).
2. **C2** — Install `report_callback_exception` so unhandled Tk callbacks log
   and toast instead of vanishing to stderr.

## Invariants checked

| Invariant | Status |
|---|---|
| UI → AppState → EventBus → Services → Repositories → Storage | Preserved |
| UI isolation | Preserved; SystemView still does not touch storage/Ollama |
| No new EventBus topics | N/A |

## Behaviour preservation

- System monitor still polls ~2s; only the thread→UI handoff changes
- Toast UI already supports `kind="error"`

## Out of scope this PR

- Repo-wide rewrite of ~50 `except Exception: pass` sites (follow-up; SystemView
  collect path now logs)
- C3–C8 chat/UX items
