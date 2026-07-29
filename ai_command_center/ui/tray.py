"""System tray — own thread, green/yellow/red status + Mission Control tooltip."""

from __future__ import annotations

import threading
from typing import Any, Callable

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
        *,
        get_status: Callable[[], dict[str, Any]] | None = None,
        on_open_approvals: Callable[[], None] | None = None,
    ) -> None:
        self._on_open = on_open
        self._on_exit = on_exit
        self._get_phase = get_phase
        self._get_status = get_status
        self._on_open_approvals = on_open_approvals
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

    def refresh(self) -> None:
        """Best-effort icon + tooltip refresh from the UI thread."""
        if self._icon is None:
            return
        try:
            phase = self._effective_phase()
            self._icon.icon = _icon(self._color_for_phase(phase))
            self._icon.title = self._tooltip()
        except Exception:
            pass

    def _effective_phase(self) -> str:
        phase = str(self._get_phase() or "idle").lower()
        status = {}
        if self._get_status is not None:
            try:
                status = dict(self._get_status() or {})
            except Exception:
                status = {}
        if status.get("pending_approvals"):
            return "busy"
        if status.get("running_executions") or status.get("active_agents"):
            return "busy" if phase in {"idle", "ready", ""} else phase
        return phase or "idle"

    def _tooltip(self) -> str:
        status: dict[str, Any] = {}
        if self._get_status is not None:
            try:
                status = dict(self._get_status() or {})
            except Exception:
                status = {}
        phase = self._effective_phase()
        queue = int(status.get("queue", 0) or 0)
        healthy = int(status.get("providers_healthy", 0) or 0)
        total = int(status.get("providers_total", 0) or 0)
        pending = int(status.get("pending_approvals", 0) or 0)
        conn = "online" if status.get("ollama_online") else "offline"
        parts = [
            f"AI Command Center · {phase}",
            f"Providers {healthy}/{total}",
            f"Queue {queue}",
            f"Ollama {conn}",
        ]
        if pending:
            parts.append(f"Approvals {pending}")
        return " · ".join(parts)

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
            return _icon(self._color_for_phase(self._effective_phase()))

        def on_open(_icon, _item) -> None:
            self._on_open()

        def on_exit(_icon, _item) -> None:
            self._on_exit()

        def on_approvals(_icon, _item) -> None:
            if self._on_open_approvals is not None:
                self._on_open_approvals()
            else:
                self._on_open()

        items = [
            pystray.MenuItem("Open", on_open, default=True),
            pystray.MenuItem("Open Approvals", on_approvals),
            pystray.MenuItem("Exit", on_exit),
        ]
        menu = pystray.Menu(*items)
        self._icon = pystray.Icon(
            "ai_command_center",
            make_icon(),
            self._tooltip(),
            menu,
        )
        try:
            self._icon.run()
        except Exception as exc:
            print(f"Tray stopped: {exc}")
        finally:
            self._running = False
