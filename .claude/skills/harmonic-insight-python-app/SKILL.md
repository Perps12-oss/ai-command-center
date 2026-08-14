---
name: harmonic-insight-python-app
description: Use for CustomTkinter desktop UI work in ai-command-center — widget structure, theming, threading into the UI, and Windows-ARM64 constraints. Triggers on: CustomTkinter widgets, window/frame layout, UI responsiveness, theming, or desktop app structure.
---

# CustomTkinter Desktop App Patterns (ACC)

UI construction standards for the ACC desktop application on
`customtkinter>=5.2.0`.

> Naming note: this skill occupies the requested `harmonic-insight-python-app`
> slot but is written for **ACC's** stack and constitution. The upstream skill of
> that name enforces a third party's brand tokens, i18n and license management —
> that content is not applicable here and was deliberately not imported.

## ACC governance deference

Local tooling under `.claude/` — **not** Level-1/2 authority (`CLAUDE.md` →
Authority). Higher authority wins:
`PROJECT_CONSTITUTION_V4.md` → `AGENTS.md` / `docs/ARCHITECTURE_ENFORCEMENT.md`
→ architecture + contracts → **Accepted** ADRs → `origin/main`.

`docs/UI_CONSTITUTION.md` is a peer domain doc under V4 — **V4 wins on
conflict**. Constitutional Pre-Flight under `docs/audits/` before implementing
(`acc-preflight`). Never writes to `docs/governance/IMPLEMENTATION_GUIDE.md`.

## Gated seams — do not weaken

- **UI isolation is strongly gated** by `arch_lint`. UI modules may not be
  imported by services, and UI may not call services directly.
- **UIQueue is event-driven; no polling at ≤100 ms** (Art. XVII). Do not add
  `self.after(50, self._poll)` refresh loops.
- **Host platform supremacy** (Inv 13) — external runtimes are capabilities
  only, never the UI's owner.
- **No global state** — no module-level `APP`, `ROOT`, or current-window handle.

## Platform reality

| Fact | Consequence |
|---|---|
| GUI is **Windows-ARM64 only** | `main.py` does not run on Linux x86_64 cloud |
| Headless needs `APPDATA` | e.g. `APPDATA=/tmp/aicc_appdata` |
| `preflight_arm64.py` expects Ollama running | env gate ≠ service availability |

**Verify UI behaviour with `create_application()` + pytest, not by launching the
desktop GUI.** A skill instruction to "run the app and look" is not executable in
this project's CI.

## Threading — the single most common CustomTkinter defect

Tkinter is not thread-safe. Widget mutation from any thread other than the one
running the mainloop causes silent corruption or a hard crash.

```python
# WRONG — mutates a widget from a worker thread
def _on_result(self, text: str) -> None:
    self.label.configure(text=text)

# RIGHT — marshal onto the UI thread
def _on_result(self, text: str) -> None:
    self.after(0, lambda: self.label.configure(text=text))
```

Bridging asyncio to the UI: the async side must never touch widgets. Publish an
event; the UI layer subscribes and marshals with `after(0, ...)`. This is also
what keeps UI isolation intact — the async service never imports the widget.

## Structure

- One class per view, constructed with its dependencies injected. No view
  reaches for a global app object.
- `CTkFrame` subclasses for composable regions; keep `__init__` to widget
  construction and wire callbacks separately so views stay testable.
- Use `grid` with explicit `rowconfigure`/`columnconfigure` weights. Mixing
  `pack` and `grid` in the same parent raises at runtime.

```python
class StatusPanel(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, *, on_retry: Callable[[], None]) -> None:
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.label = ctk.CTkLabel(self, text="")
        self.label.grid(row=0, column=0, sticky="ew", padx=8, pady=4)
        self.retry = ctk.CTkButton(self, text="Retry", command=on_retry)
        self.retry.grid(row=1, column=0, sticky="e", padx=8, pady=4)
```

## Theming

- Set appearance once at startup:
  `ctk.set_appearance_mode("system")`, `ctk.set_default_color_theme(...)`.
- Never hardcode hex colors inline per widget — resolve from one theme module so
  light/dark both stay legible.
- Respect the user's system mode by default; an explicit override belongs in
  settings, not scattered `configure(fg_color=...)` calls.

## Responsiveness

- No blocking work in a callback. Anything over ~16 ms belongs on a worker with
  results marshalled back via `after(0, ...)`.
- Widget creation is expensive — for long lists, reuse widgets rather than
  destroying and recreating them.
- Always `destroy()` views you drop, and cancel any pending `after` ids on
  teardown, or callbacks fire against dead widgets during shutdown.

## Review checklist

- [ ] No widget touched off the mainloop thread
- [ ] No `after()` polling loop at ≤100 ms
- [ ] No service imported by a UI module (and vice versa)
- [ ] No module-level app/root/window global
- [ ] Pending `after` ids cancelled on teardown
- [ ] Verified via `create_application()` + pytest, not a manual GUI launch
