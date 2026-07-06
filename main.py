"""AI Command Center — desktop entry with command palette UI."""

from __future__ import annotations

import sys

from ai_command_center.application import create_application
from ai_command_center.platform.detector import is_arm64
from ai_command_center.core.events.topics import UI_ORCHESTRATION_INSPECTOR_OPEN
from ai_command_center.ui.app import CommandPaletteApp
from ai_command_center.ui.orchestration_inspector import OrchestrationInspector
from ai_command_center.ui.tray import TrayController
from ai_command_center.ui.workspace_os_inspector import WorkspaceOsInspector
from ai_command_center.utils.hotkey import register_hotkey, validate_hotkey


def main() -> int:
    if not is_arm64():
        print("ERROR: Native ARM64 Python required.", file=sys.stderr)
        return 1

    ok, detail = validate_hotkey()
    if not ok:
        print(f"WARNING: Hotkey unavailable: {detail}", file=sys.stderr)

    core = create_application()
    core.startup()

    app = CommandPaletteApp(
        core.bus,
        core.state_store,
        workspace_os_enabled=core.workspace_os is not None and core.workspace_os.enabled,
    )
    shutting_down = False
    inspector: WorkspaceOsInspector | None = None
    orch_inspector: OrchestrationInspector | None = None

    def shutdown() -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        tray.stop()
        try:
            if inspector is not None:
                inspector.destroy()
        except Exception:
            pass
        try:
            if orch_inspector is not None:
                orch_inspector.destroy()
        except Exception:
            pass
        try:
            app.destroy()
        except Exception:
            pass
        core.shutdown()

    def show_palette() -> None:
        app.after(0, app.show)

    def toggle_palette() -> None:
        app.after(0, app.toggle)

    def toggle_inspector() -> None:
        nonlocal inspector
        if inspector is not None and inspector.winfo_exists():
            inspector.after(0, inspector.destroy)
            inspector = None
            return
        if core.workspace_os is not None and core.workspace_os.enabled:
            inspector = WorkspaceOsInspector(
                app, core.bus, core.state_store, ui_queue=app._ui_queue
            )

    def toggle_orchestration_inspector() -> None:
        nonlocal orch_inspector
        if orch_inspector is not None and orch_inspector.winfo_exists():
            orch_inspector.after(0, orch_inspector.destroy)
            orch_inspector = None
            return
        orch_inspector = OrchestrationInspector(
            app, core.bus, core.state_store, ui_queue=app._ui_queue
        )

    def _on_orchestration_inspector_open(_event=None) -> None:
        app.after(0, toggle_orchestration_inspector)

    core.bus.subscribe(
        UI_ORCHESTRATION_INSPECTOR_OPEN,
        lambda _event: _on_orchestration_inspector_open(),
    )

    tray = TrayController(
        on_open=show_palette,
        on_exit=lambda: app.after(0, shutdown),
        get_phase=app.tray_phase,
    )
    tray.start()

    hotkey = core.state_store.snapshot.settings.hotkey or "alt+space"
    hk_ok, hk_msg = register_hotkey(hotkey, toggle_palette)
    if hk_ok:
        print(f"Hotkey: {hk_msg}")
    else:
        print(f"Hotkey fallback (tray only): {hk_msg}", file=sys.stderr)

    # Workspace OS Inspector hotkey (Track B - Phase 2)
    inspector_ok, inspector_msg = register_hotkey("ctrl+shift+w", toggle_inspector)
    if inspector_ok:
        print(f"Workspace OS Inspector hotkey: {inspector_msg}")
    else:
        print(f"Workspace OS Inspector hotkey unavailable: {inspector_msg}", file=sys.stderr)

    orch_inspector_ok, orch_inspector_msg = register_hotkey(
        "ctrl+shift+o", toggle_orchestration_inspector
    )
    if orch_inspector_ok:
        print(f"Orchestration Inspector hotkey: {orch_inspector_msg}")
    else:
        print(
            f"Orchestration Inspector hotkey unavailable: {orch_inspector_msg}",
            file=sys.stderr,
        )

    print(
        "AI Command Center running. Alt+Space to toggle palette. "
        "Ctrl+Shift+W for Workspace OS Inspector. "
        "Ctrl+Shift+O for Orchestration Inspector. Tray icon active."
    )
    app.protocol("WM_DELETE_WINDOW", app.hide)
    app.show()

    try:
        app.mainloop()
    finally:
        shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
