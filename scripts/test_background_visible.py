#!/usr/bin/env python3

"""Regression test — blurred global wallpaper visible on every page."""



from __future__ import annotations



import sys

from pathlib import Path



PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))



from ai_command_center.core.app_state import AppStateStore

from ai_command_center.core.event_bus import EventBus

from ai_command_center.ui.app import VIEW_IDS, CommandPaletteApp





class _HeadlessApp(CommandPaletteApp):

    """Minimal shell for background visibility checks without fade/hotkey."""



    def __init__(self, bus: EventBus, state_store: AppStateStore) -> None:

        super().__init__(bus, state_store)

        self.deiconify()

        self.attributes("-alpha", 1.0)





def _assert_backdrop(app: CommandPaletteApp, page: str) -> list[str]:

    errors: list[str] = []

    shell = app._shell_backdrop

    canvas = shell.canvas

    tags = canvas.find_withtag("bg")

    if not tags:

        errors.append(f"{page}: canvas missing bg tag")

    if not shell.image_loaded:

        errors.append(f"{page}: wallpaper not loaded")

    if canvas.find_withtag("zone_motion"):

        errors.append(f"{page}: zone_motion green border must not persist")

    if page == "home":

        if not canvas.find_withtag("zone_ui"):

            errors.append(f"{page}: home zone create_window hosts missing")

    else:

        if not canvas.find_withtag("page_view"):

            errors.append(f"{page}: page_view create_window missing (overlay may block canvas)")

        if canvas.find_withtag("zone_ui"):

            errors.append(f"{page}: home zone_ui bleeding onto non-home page")

    return errors





def main() -> int:

    print("=== Background visibility (all pages) ===")

    failures: list[str] = []



    bus = EventBus()

    store = AppStateStore(bus)

    root = _HeadlessApp(bus, store)

    root.update_idletasks()

    root.update()



    for page in VIEW_IDS:

        root._navigate(page)

        root.update_idletasks()

        root.update()

        failures.extend(_assert_backdrop(root, page))

        view = root._views.get(page)

        if view is not None and hasattr(view, "background_canvas"):

            bc = view.background_canvas

            if bc.winfo_ismapped():

                failures.append(f"{page}: per-page BackgroundCanvas must be hidden")



    print(f"Checked pages: {', '.join(VIEW_IDS)}")

    if failures:

        print("FAIL:")

        for item in failures:

            print(f"  - {item}")

        root.destroy()

        return 1



    print("PASS: blurred command_center_bg visible on all pages")

    root.destroy()

    return 0





if __name__ == "__main__":

    raise SystemExit(main())

