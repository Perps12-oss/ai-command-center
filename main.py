"""AI Command Center — desktop entry with command palette UI."""

from __future__ import annotations

import sys

from ai_command_center.application import create_application
from ai_command_center.platform.detector import is_arm64
from ai_command_center.platform.hotkey_provider import get_hotkey_provider
from ai_command_center.core.events.topics import UI_ORCHESTRATION_INSPECTOR_OPEN
from ai_command_center.ui.app import CommandPaletteApp
from ai_command_center.ui.orchestration_inspector import OrchestrationInspector
from ai_command_center.ui.runtime_inspector import RuntimeInspector
from ai_command_center.ui.tray import TrayController
from ai_command_center.ui.workspace_os_inspector import WorkspaceOsInspector


def main() -> int:
    if not is_arm64():
        print("ERROR: Native ARM64 Python required.", file=sys.stderr)
        return 1

    hotkey_provider = get_hotkey_provider()
    ok, detail = hotkey_provider.validate("alt+space")
    if not ok:
        print(f"WARNING: Hotkey unavailable: {detail}", file=sys.stderr)

    core = create_application()
    core.startup()

    app = CommandPaletteApp(
        core.bus,
        core.state_store,
        workspace_os_enabled=core.workspace_os is not None and core.workspace_os.enabled,
    )
    ui_queue = app._ui_queue
    shutting_down = False
    inspector: WorkspaceOsInspector | None = None
    orch_inspector: OrchestrationInspector | None = None
    runtime_inspector: RuntimeInspector | None = None

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
            if runtime_inspector is not None:
                runtime_inspector.destroy()
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
        ui_queue.enqueue(app.show)

    def toggle_palette() -> None:
        ui_queue.enqueue(app.toggle)

    def _toggle_inspector() -> None:
        nonlocal inspector
        if inspector is not None and inspector.winfo_exists():
            inspector.destroy()
            inspector = None
            return
        if core.workspace_os is not None and core.workspace_os.enabled:
            inspector = WorkspaceOsInspector(
                app, core.bus, core.state_store, ui_queue=ui_queue
            )

    def toggle_inspector() -> None:
        ui_queue.enqueue(_toggle_inspector)

    def _toggle_runtime_inspector() -> None:
        nonlocal runtime_inspector
        if runtime_inspector is not None and runtime_inspector.winfo_exists():
            runtime_inspector.destroy()
            runtime_inspector = None
            return
        runtime_inspector = RuntimeInspector(
            app, core.bus, core.state_store, ui_queue=ui_queue
        )

    def toggle_runtime_inspector() -> None:
        ui_queue.enqueue(_toggle_runtime_inspector)

    def _toggle_orchestration_inspector() -> None:
        nonlocal orch_inspector
        if orch_inspector is not None and orch_inspector.winfo_exists():
            orch_inspector.destroy()
            orch_inspector = None
            return
        orch_inspector = OrchestrationInspector(
            app, core.bus, core.state_store, ui_queue=ui_queue
        )

    def toggle_orchestration_inspector() -> None:
        ui_queue.enqueue(_toggle_orchestration_inspector)

    def _on_orchestration_inspector_open(_event=None) -> None:
        ui_queue.enqueue(_toggle_orchestration_inspector)

    core.bus.subscribe(
        UI_ORCHESTRATION_INSPECTOR_OPEN,
        lambda _event: _on_orchestration_inspector_open(),
    )

    tray = TrayController(
        on_open=show_palette,
        on_exit=lambda: ui_queue.enqueue(shutdown),
        get_phase=app.tray_phase,
    )
    tray.start()

    settings = core.state_store.snapshot.settings
    overlay_hotkey = settings.overlay_hotkey or settings.hotkey or "alt+space"
    hk_ok, hk_msg = hotkey_provider.register(overlay_hotkey, toggle_palette)
    if hk_ok:
        print(f"Hotkey: {hk_msg}")
    else:
        print(f"Hotkey fallback (tray only): {hk_msg}", file=sys.stderr)

    inspector_ok, inspector_msg = hotkey_provider.register("ctrl+shift+w", toggle_inspector)
    if inspector_ok:
        print(f"Workspace OS Inspector hotkey: {inspector_msg}")
    else:
        print(f"Workspace OS Inspector hotkey unavailable: {inspector_msg}", file=sys.stderr)

    orch_inspector_ok, orch_inspector_msg = hotkey_provider.register(
        "ctrl+shift+o", toggle_orchestration_inspector
    )
    runtime_inspector_ok, runtime_inspector_msg = hotkey_provider.register(
        "ctrl+shift+r", toggle_runtime_inspector
    )
    if orch_inspector_ok:
        print(f"Orchestration Inspector hotkey: {orch_inspector_msg}")
    else:
        print(
            f"Orchestration Inspector hotkey unavailable: {orch_inspector_msg}",
            file=sys.stderr,
        )
    if runtime_inspector_ok:
        print(f"Runtime Inspector hotkey: {runtime_inspector_msg}")
    else:
        print(
            f"Runtime Inspector hotkey unavailable: {runtime_inspector_msg}",
            file=sys.stderr,
        )

    print(
        "AI Command Center running. Alt+Space to toggle palette. "
        "Ctrl+Shift+W for Workspace OS Inspector. "
        "Ctrl+Shift+O for Orchestration Inspector. "
        "Ctrl+Shift+R for Runtime Inspector. Tray icon active."
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
