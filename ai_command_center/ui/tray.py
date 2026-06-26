"""System tray — own thread, green/yellow/red status."""

from __future__ import annotations

import threading
from typing import Callable

from PIL import Image, ImageDraw


def _icon(color: str, size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, size - 8, size - 8), fill=color)
    return img


class TrayController:
    def __init__(
        self,
        on_open: Callable[[], None],
        on_exit: Callable[[], None],
        get_phase: Callable[[], str],
    ) -> None:
        self._on_open = on_open
        self._on_exit = on_exit
        self._get_phase = get_phase
        self._icon = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, name="system-tray", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass

    def _color_for_phase(self, phase: str) -> str:
        if phase in {"starting", "busy"}:
            return "#EAB308"
        if phase in {"error", "stopped"}:
            return "#EF4444"
        return "#22C55E"

    def _run(self) -> None:
        try:
            import pystray
        except Exception as exc:
            print(f"Tray unavailable: {exc}")
            self._running = False
            return

        def make_icon() -> Image.Image:
            return _icon(self._color_for_phase(self._get_phase()))

        def on_open(_icon, _item) -> None:
            self._on_open()

        def on_exit(_icon, _item) -> None:
            self._on_exit()

        menu = pystray.Menu(
            pystray.MenuItem("Open", on_open, default=True),
            pystray.MenuItem("Exit", on_exit),
        )
        self._icon = pystray.Icon(
            "ai_command_center",
            make_icon(),
            "AI Command Center",
            menu,
        )
        try:
            self._icon.run()
        except Exception as exc:
            print(f"Tray stopped: {exc}")
        finally:
            self._running = False
