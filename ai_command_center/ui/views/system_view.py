"""System monitor — CPU, RAM, process info via psutil (Phase 4+)."""

from __future__ import annotations

import threading
import time

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.theme import tokens as T

try:
    import psutil as _psutil
    _PSUTIL = True
except ImportError:
    _psutil = None  # type: ignore[assignment]
    _PSUTIL = False


def _pct_color(pct: float) -> str:
    if pct >= 85:
        return T.STATUS_ERROR
    if pct >= 60:
        return T.STATUS_BUSY
    return T.STATUS_READY


class _MeterBar(ctk.CTkFrame):
    """Label + progress bar pair for a single metric."""

    def __init__(self, master, label: str) -> None:
        super().__init__(master, fg_color="transparent")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text=label, font=T.FONT_SMALL, text_color=T.TEXT_MUTED, width=80, anchor="w").pack(side="left")
        self._value_lbl = ctk.CTkLabel(row, text="—", font=T.FONT_SMALL, text_color=T.TEXT_PRIMARY, width=80, anchor="e")
        self._value_lbl.pack(side="right")
        self._bar = ctk.CTkProgressBar(self, height=6, corner_radius=3, progress_color=T.STATUS_READY)
        self._bar.pack(fill="x", pady=(3, 8))
        self._bar.set(0)

    def update(self, pct: float, label: str) -> None:
        self._bar.set(pct / 100)
        self._bar.configure(progress_color=_pct_color(pct))
        self._value_lbl.configure(text=label)


class SystemView(ctk.CTkFrame):
    """System resource monitor.

    Polls psutil on a background thread and pushes updates to the UI
    via `after()` on the main thread — no EventBus interaction.
    """

    _POLL_MS = 2000

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._active = False
        self._build()

    def _build(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color=T.BG_PANEL, corner_radius=0, height=44)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="System Monitor", font=T.FONT_HEADER, text_color=T.TEXT_PRIMARY).pack(side="left", padx=T.PAD, pady=10)
        self._refresh_lbl = ctk.CTkLabel(header, text="", font=T.FONT_SMALL, text_color=T.TEXT_MUTED)
        self._refresh_lbl.pack(side="right", padx=T.PAD)

        scroll = ctk.CTkScrollableFrame(self, fg_color=T.BG_DEEP, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        if not _PSUTIL:
            ctk.CTkLabel(
                scroll,
                text="psutil not available — install with: pip install psutil",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
            ).pack(padx=T.PAD, pady=T.PAD)
            return

        # Meters card
        card = GlassCard(scroll)
        card.pack(fill="x", padx=T.PAD, pady=T.PAD)
        ctk.CTkLabel(card, text="RESOURCES", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w").pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._cpu_bar = _MeterBar(card, "CPU")
        self._cpu_bar.pack(fill="x", padx=T.PAD)
        self._ram_bar = _MeterBar(card, "RAM")
        self._ram_bar.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        # Process info card
        info_card = GlassCard(scroll)
        info_card.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))
        ctk.CTkLabel(info_card, text="PROCESS", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w").pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))
        self._proc_lbl = ctk.CTkLabel(info_card, text="—", font=T.FONT_SMALL, text_color=T.TEXT_SECONDARY, anchor="w", justify="left")
        self._proc_lbl.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        # Top processes card
        top_card = GlassCard(scroll)
        top_card.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))
        ctk.CTkLabel(top_card, text="TOP PROCESSES (CPU)", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w").pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))
        self._top_lbl = ctk.CTkLabel(top_card, text="—", font=T.FONT_MONO, text_color=T.TEXT_SECONDARY, anchor="w", justify="left")
        self._top_lbl.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        self._start_polling()

    def _start_polling(self) -> None:
        self._active = True
        self.after(100, self._poll)

    def _poll(self) -> None:
        if not _PSUTIL or not self._active:
            return
        t = threading.Thread(target=self._collect, daemon=True)
        t.start()

    def _collect(self) -> None:
        try:
            cpu = _psutil.cpu_percent(interval=0.5)
            vm = _psutil.virtual_memory()
            proc = _psutil.Process()
            proc_mem = proc.memory_info().rss / 1024 / 1024
            proc_cpu = proc.cpu_percent(interval=0.1)

            procs = []
            for p in _psutil.process_iter(["pid", "name", "cpu_percent"]):
                try:
                    procs.append((p.info["cpu_percent"] or 0, p.info["name"], p.info["pid"]))
                except Exception:
                    pass
            procs.sort(reverse=True)
            top5 = procs[:5]

            self.after(0, lambda: self._update_ui(cpu, vm, proc_cpu, proc_mem, top5))
        except Exception:
            pass
        self.after(self._POLL_MS, self._poll)

    def _update_ui(self, cpu: float, vm, proc_cpu: float, proc_mem: float, top5: list) -> None:
        if not _PSUTIL:
            return
        self._cpu_bar.update(cpu, f"{cpu:.0f}%")
        ram_pct = vm.percent
        ram_used = vm.used / 1024 / 1024 / 1024
        ram_total = vm.total / 1024 / 1024 / 1024
        self._ram_bar.update(ram_pct, f"{ram_used:.1f} / {ram_total:.1f} GB")

        self._proc_lbl.configure(
            text=f"This process — CPU: {proc_cpu:.1f}%   RAM: {proc_mem:.0f} MB"
        )

        lines = "\n".join(
            f"{pct:5.1f}%  {name[:28]:<28}  pid {pid}"
            for pct, name, pid in top5
        )
        self._top_lbl.configure(text=lines or "—")
        self._refresh_lbl.configure(text=f"Updated {time.strftime('%H:%M:%S')}")

    def on_hide(self) -> None:
        self._active = False

    def on_show(self) -> None:
        if not self._active:
            self._active = True
            self._poll()
