"""System monitor — CPU/RAM/Disk/Net meters, sparkline, top processes, tool log, error log."""
from __future__ import annotations

import threading
import time
from collections import deque

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T

_MAX_LOG_ROWS = 50


# ──────────────────────────────────────────────────────────────────────────────
#  Generic scrollable event-log card (shared by tool log + error log)
# ──────────────────────────────────────────────────────────────────────────────

class _EventLogCard(ctk.CTkFrame):
    """Scrollable list of timestamped log entries with optional colour coding."""

    def __init__(self, master, title: str, empty_msg: str, max_rows: int = _MAX_LOG_ROWS) -> None:
        super().__init__(master, fg_color=T.BG_GLASS, border_color=T.BG_GLASS_BORDER, border_width=1, corner_radius=T.CARD_RADIUS)
        self._max_rows = max_rows
        self._empty_msg = empty_msg
        self._entries: deque[tuple[str, str, str]] = deque(maxlen=max_rows)  # (ts, text, color)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=T.PAD, pady=(8, 4))
        ctk.CTkLabel(hdr, text=title, font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w").pack(side="left")
        self._count_lbl = ctk.CTkLabel(hdr, text="", font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="e")
        self._count_lbl.pack(side="right")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=T.PAD, pady=(0, 4))
        ctk.CTkButton(
            btn_row, text="Clear", width=54, height=22,
            font=T.FONT_SMALL, fg_color=T.BG_GLASS, hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED, corner_radius=T.SMALL_RADIUS,
            command=self.clear,
        ).pack(side="right")

        self._scroll = ctk.CTkScrollableFrame(self, fg_color=T.BG_DEEP, corner_radius=0, height=140)
        self._scroll.pack(fill="x", padx=0, pady=(0, 0))
        self._render()

    def push(self, text: str, color: str | None = None) -> None:
        ts = time.strftime("%H:%M:%S")
        self._entries.appendleft((ts, text, color or T.TEXT_SECONDARY))
        self._render()

    def clear(self) -> None:
        self._entries.clear()
        self._render()

    def load_errors(self, errors: tuple[str, ...]) -> None:
        """Bulk-load from AppState.errors — replaces current contents."""
        self._entries.clear()
        for msg in reversed(errors):
            self._entries.appendleft(("—", msg, T.STATUS_ERROR))
        self._render()

    def _render(self) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()
        count = len(self._entries)
        self._count_lbl.configure(text=f"{count}" if count else "")
        if not self._entries:
            ctk.CTkLabel(
                self._scroll, text=self._empty_msg,
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w",
            ).pack(fill="x", padx=T.PAD, pady=6)
            return
        for ts, text, color in self._entries:
            row = ctk.CTkFrame(self._scroll, fg_color="transparent")
            row.pack(fill="x", padx=T.PAD, pady=(1, 1))
            ctk.CTkLabel(row, text=ts, font=T.FONT_MONO, text_color=T.TEXT_MUTED, width=68, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=text, font=T.FONT_SMALL, text_color=color, anchor="w", wraplength=480, justify="left").pack(side="left", fill="x", expand=True)

_SERVICE_STATE_COLOR = {
    "ready":    "#22C55E",
    "starting": "#EAB308",
    "degraded": "#EAB308",
    "error":    "#EF4444",
    "stopped":  "#3A3A5A",
    "stopping": "#3A3A5A",
}
_SERVICE_SLOTS = 60


class _ServiceHealthTimeline(ctk.CTkFrame):
    """Compact per-service sparkline of state transitions (last 60 ticks)."""

    def __init__(self, master) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.CARD_RADIUS,
        )
        ctk.CTkLabel(
            self, text="SERVICE HEALTH TIMELINE",
            font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w",
        ).pack(fill="x", padx=T.PAD, pady=(8, 4))

        self._rows: dict[str, tuple[ctk.CTkCanvas, ctk.CTkLabel]] = {}
        self._history: dict[str, deque[str]] = {}
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="x", padx=T.PAD, pady=(0, 8))

    def _ensure_row(self, service: str) -> None:
        if service in self._rows:
            return
        self._history[service] = deque(["stopped"] * _SERVICE_SLOTS, maxlen=_SERVICE_SLOTS)
        row = ctk.CTkFrame(self._body, fg_color="transparent")
        row.pack(fill="x", pady=(2, 0))
        name_lbl = ctk.CTkLabel(
            row, text=service[:22], font=T.FONT_MONO, text_color=T.TEXT_SECONDARY,
            width=140, anchor="w",
        )
        name_lbl.pack(side="left")
        canvas = ctk.CTkCanvas(row, height=12, bg=T.BG_DEEP, highlightthickness=0)
        canvas.pack(side="left", fill="x", expand=True, padx=(4, 0))
        state_lbl = ctk.CTkLabel(
            row, text="stopped", font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED, width=60, anchor="e",
        )
        state_lbl.pack(side="right", padx=(4, 0))
        self._rows[service] = (canvas, state_lbl)

    def push_service_state(self, service: str, state: str) -> None:
        self._ensure_row(service)
        self._history[service].append(state.lower())
        canvas, state_lbl = self._rows[service]
        color = _SERVICE_STATE_COLOR.get(state.lower(), T.TEXT_MUTED)
        state_lbl.configure(text=state.lower(), text_color=color)
        self._redraw(service)

    def _redraw(self, service: str) -> None:
        canvas, _ = self._rows[service]
        canvas.update_idletasks()
        w = canvas.winfo_width() or 300
        h = 12
        canvas.delete("all")
        slots = list(self._history[service])
        slot_w = max(1, w / _SERVICE_SLOTS)
        for i, state in enumerate(slots):
            x0 = int(i * slot_w)
            x1 = max(x0 + 1, int((i + 1) * slot_w) - 1)
            color = _SERVICE_STATE_COLOR.get(state, T.BG_GLASS_BORDER)
            canvas.create_rectangle(x0, 1, x1, h - 1, fill=color, outline="")


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


def _human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}/s"
        n /= 1024
    return f"{n:.1f} GB/s"


# ──────────────────────────────────────────────────────────────────────────────
#  Meter bar
# ──────────────────────────────────────────────────────────────────────────────

class _MeterBar(ctk.CTkFrame):
    def __init__(self, master, label: str) -> None:
        super().__init__(master, fg_color="transparent")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(
            row, text=label, font=T.FONT_SMALL, text_color=T.TEXT_MUTED, width=80, anchor="w"
        ).pack(side="left")
        self._value_lbl = ctk.CTkLabel(
            row, text="\u2014", font=T.FONT_SMALL, text_color=T.TEXT_PRIMARY, width=120, anchor="e"
        )
        self._value_lbl.pack(side="right")
        self._bar = ctk.CTkProgressBar(self, height=6, corner_radius=T.PROGRESS_RADIUS, progress_color=T.STATUS_READY)
        self._bar.pack(fill="x", pady=(3, 8))
        self._bar.set(0)

    def update(self, pct: float, label: str) -> None:
        self._bar.set(pct / 100)
        self._bar.configure(progress_color=_pct_color(pct))
        self._value_lbl.configure(text=label)


# ──────────────────────────────────────────────────────────────────────────────
#  Sparkline canvas
# ──────────────────────────────────────────────────────────────────────────────

class _Sparkline(ctk.CTkFrame):
    """Rolling 60-point line chart drawn on a CTkCanvas."""

    _POINTS = 60
    _H = 52
    _W = 0  # determined at draw time

    def __init__(self, master, label: str, color: str = T.STATUS_READY) -> None:
        super().__init__(master, fg_color="transparent")
        self._color   = color
        self._history: list[float] = [0.0] * self._POINTS

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=label, font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="w").pack(side="left")
        self._peak_lbl = ctk.CTkLabel(hdr, text="", font=T.FONT_SMALL, text_color=T.TEXT_MUTED, anchor="e")
        self._peak_lbl.pack(side="right")

        self._canvas = ctk.CTkCanvas(self, height=self._H, bg=T.BG_DEEP, highlightthickness=0)
        self._canvas.pack(fill="x", pady=(2, 0))

    def push(self, value: float) -> None:
        self._history.append(max(0.0, min(100.0, value)))
        if len(self._history) > self._POINTS:
            self._history.pop(0)
        self._peak_lbl.configure(text=f"peak {max(self._history):.0f}%")
        self._draw()

    def _draw(self, no_color_updates: bool = False, **kwargs) -> None:
        if not hasattr(self, "_history"):
            return
        c = self._canvas
        c.delete("all")
        w = c.winfo_width() or 400
        h = self._H
        n = len(self._history)
        if n < 2:
            return
        step = w / (n - 1)
        pts: list[float] = []
        for i, v in enumerate(self._history):
            x = i * step
            y = h - (v / 100.0) * (h - 4) - 2
            pts.extend([x, y])
        if len(pts) >= 4:
            c.create_line(*pts, fill=self._color, width=1, smooth=True)
        # fill under line
        fill_pts = [0, h] + pts + [pts[-2], h]
        c.create_polygon(*fill_pts, fill=self._color, stipple="gray25", outline="")


# ──────────────────────────────────────────────────────────────────────────────
#  I/O tile (disk or net)
# ──────────────────────────────────────────────────────────────────────────────

class _IOTile(ctk.CTkFrame):
    def __init__(self, master, title: str, in_label: str, out_label: str) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.CARD_RADIUS,
        )
        ctk.CTkLabel(self, text=title, font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w").pack(fill="x", padx=10, pady=(8, 4))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 8))

        self._in_lbl  = self._stat(row, in_label,  side="left")
        self._out_lbl = self._stat(row, out_label, side="right")

    @staticmethod
    def _stat(parent, label: str, side: str) -> ctk.CTkLabel:
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.pack(side=side, fill="both", expand=True)
        ctk.CTkLabel(col, text=label, font=(T.FONT_FAMILY, 10), text_color=T.TEXT_MUTED, anchor="center").pack(fill="x")
        val = ctk.CTkLabel(col, text="\u2014", font=T.FONT_SMALL, text_color=T.TEXT_PRIMARY, anchor="center")
        val.pack(fill="x")
        return val

    def update(self, in_val: str, out_val: str) -> None:
        self._in_lbl.configure(text=in_val)
        self._out_lbl.configure(text=out_val)


# ──────────────────────────────────────────────────────────────────────────────
#  Process table
# ──────────────────────────────────────────────────────────────────────────────

class _ProcessTable(ctk.CTkFrame):
    """Sortable, filterable top-process table."""

    _SORT_KEY = {
        "cpu": lambda p: p[1],
        "mem": lambda p: p[2],
        "pid": lambda p: p[0],
        "name": lambda p: p[3].lower(),
    }

    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self._procs: list[tuple[int, float, float, str]] = []
        self._sort_col = "cpu"
        self._sort_desc = True
        self._filter = ""

        self._search = ctk.CTkEntry(
            self,
            placeholder_text="Filter processes…",
            font=T.FONT_BODY,
            height=28,
            fg_color=T.BG_INPUT,
            border_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_PRIMARY,
        )
        self._search.pack(fill="x", padx=T.PAD, pady=(0, 6))
        self._search.bind("<KeyRelease>", lambda _e: self._apply_filter())

        hdr = ctk.CTkFrame(self, fg_color=T.BG_PANEL, height=26)
        hdr.pack(fill="x", padx=T.PAD)
        hdr.pack_propagate(False)
        self._headers: dict[str, ctk.CTkLabel] = {}
        for col, title, width in (
            ("cpu", "CPU", 70),
            ("mem", "MEM", 70),
            ("pid", "PID", 70),
            ("name", "NAME", 0),
        ):
            lbl = ctk.CTkLabel(
                hdr,
                text=title,
                font=T.FONT_ROLE,
                text_color=T.TEXT_MUTED,
                width=width,
                anchor="w" if col == "name" else "e",
            )
            lbl.pack(side="left" if col == "name" else "right", padx=(8, 0) if col == "name" else (4, 0))
            lbl.bind("<Button-1>", lambda _e, c=col: self._set_sort(c))
            self._headers[col] = lbl

        self._rows = ctk.CTkFrame(self, fg_color="transparent")
        self._rows.pack(fill="x", padx=T.PAD, pady=(4, 0))
        self._rows.columnconfigure(0, weight=1)

    def _set_sort(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = col
            self._sort_desc = True
        self._render()

    def _apply_filter(self) -> None:
        self._filter = self._search.get().strip().lower()
        self._render()

    def set_data(self, procs: list[tuple[int, float, float, str]]) -> None:
        self._procs = procs
        self._render()

    def _render(self) -> None:
        for w in self._rows.winfo_children():
            w.destroy()

        shown = [p for p in self._procs if self._filter in p[3].lower()]
        shown.sort(key=self._SORT_KEY[self._sort_col], reverse=self._sort_desc)
        for col, lbl in self._headers.items():
            marker = " ▼" if self._sort_col == col and self._sort_desc else " ▲" if self._sort_col == col else ""
            base = {"cpu": "CPU", "mem": "MEM", "pid": "PID", "name": "NAME"}[col]
            lbl.configure(text=base + marker)

        if not shown:
            ctk.CTkLabel(
                self._rows,
                text="No processes match",
                font=T.FONT_BODY,
                text_color=T.TEXT_MUTED,
            ).pack(pady=8)
            return

        for pid, cpu, mem, name in shown[:15]:
            row = ctk.CTkFrame(self._rows, fg_color="transparent")
            row.pack(fill="x", pady=(1, 1))
            ctk.CTkLabel(row, text=f"{cpu:5.1f}%", font=T.FONT_MONO, text_color=T.TEXT_SECONDARY, width=70, anchor="e").pack(side="right", padx=(4, 0))
            ctk.CTkLabel(row, text=f"{mem:5.1f}%", font=T.FONT_MONO, text_color=T.TEXT_SECONDARY, width=70, anchor="e").pack(side="right", padx=(4, 0))
            ctk.CTkLabel(row, text=str(pid), font=T.FONT_MONO, text_color=T.TEXT_SECONDARY, width=70, anchor="e").pack(side="right", padx=(4, 0))
            ctk.CTkLabel(row, text=name[:36], font=T.FONT_MONO, text_color=T.TEXT_PRIMARY, anchor="w").pack(side="left", fill="x", expand=True, padx=(8, 0))


# ──────────────────────────────────────────────────────────────────────────────
#  SystemView
# ──────────────────────────────────────────────────────────────────────────────

class SystemView(ctk.CTkFrame):
    """System resource monitor.

    Polls psutil on a background thread; pushes results to the UI via after()
    on the main thread. No EventBus interaction.
    """

    _POLL_MS = 2000

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._active        = False
        self._prev_disk     = None
        self._prev_net      = None
        self._prev_ts       = None
        self._build()

    def _build(self) -> None:
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

        # ── Resource meters + sparklines ───────────────────────────────────────
        meters_card = GlassCard(scroll)
        meters_card.pack(fill="x", padx=T.PAD, pady=T.PAD)
        ctk.CTkLabel(meters_card, text="RESOURCES", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w").pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._cpu_bar = _MeterBar(meters_card, "CPU")
        self._cpu_bar.pack(fill="x", padx=T.PAD)
        self._cpu_spark = _Sparkline(meters_card, "CPU history", T.ACCENT_DEFAULT)
        self._cpu_spark.pack(fill="x", padx=T.PAD, pady=(0, 4))

        self._ram_bar = _MeterBar(meters_card, "RAM")
        self._ram_bar.pack(fill="x", padx=T.PAD)
        self._ram_spark = _Sparkline(meters_card, "RAM history", T.STATUS_BUSY)
        self._ram_spark.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        # ── I/O tiles ──────────────────────────────────────────────────────────
        io_row = ctk.CTkFrame(scroll, fg_color="transparent")
        io_row.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))
        io_row.columnconfigure((0, 1), weight=1, uniform="io")

        self._disk_tile = _IOTile(io_row, "DISK I/O", "Read", "Write")
        self._disk_tile.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self._net_tile = _IOTile(io_row, "NETWORK I/O", "Recv", "Sent")
        self._net_tile.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # ── Process info ───────────────────────────────────────────────────────
        info_card = GlassCard(scroll)
        info_card.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))
        ctk.CTkLabel(info_card, text="PROCESS", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w").pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))
        self._proc_lbl = ctk.CTkLabel(info_card, text="\u2014", font=T.FONT_SMALL, text_color=T.TEXT_SECONDARY, anchor="w", justify="left")
        self._proc_lbl.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        # ── Top processes ──────────────────────────────────────────────────────
        top_card = GlassCard(scroll)
        top_card.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))
        ctk.CTkLabel(top_card, text="TOP PROCESSES", font=T.FONT_ROLE, text_color=T.TEXT_MUTED, anchor="w").pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))
        self._top_table = _ProcessTable(top_card)
        self._top_table.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        # ── Service health timeline ─────────────────────────────────────────
        self._service_timeline = _ServiceHealthTimeline(scroll)
        self._service_timeline.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        # ── Tool execution log ──────────────────────────────────────────────
        self._tool_log = _EventLogCard(
            scroll, "TOOL EXECUTION LOG", "No tool runs yet."
        )
        self._tool_log.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        # ── App error log ───────────────────────────────────────────────────
        self._error_log = _EventLogCard(
            scroll, "APP ERROR LOG", "No errors recorded.", max_rows=20
        )
        self._error_log.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

        self._start_polling()

    def _start_polling(self) -> None:
        self._active = True
        self.after(100, self._poll)

    def _poll(self) -> None:
        if not _PSUTIL or not self._active:
            return
        threading.Thread(target=self._collect, daemon=True).start()

    def _collect(self) -> None:
        try:
            now  = time.monotonic()
            cpu  = _psutil.cpu_percent(interval=0.5)
            vm   = _psutil.virtual_memory()
            proc = _psutil.Process()
            proc_mem = proc.memory_info().rss / 1024 / 1024
            proc_cpu = proc.cpu_percent(interval=0.1)

            procs: list[tuple[int, float, float, str]] = []
            for p in _psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    procs.append((
                        p.info["pid"],
                        p.info["cpu_percent"] or 0.0,
                        p.info["memory_percent"] or 0.0,
                        str(p.info["name"] or ""),
                    ))
                except Exception:
                    pass

            # Disk I/O delta
            disk_delta = (None, None)
            try:
                dk = _psutil.disk_io_counters()
                if dk and self._prev_disk and self._prev_ts:
                    dt = max(now - self._prev_ts, 0.001)
                    read_s  = (dk.read_bytes  - self._prev_disk.read_bytes)  / dt
                    write_s = (dk.write_bytes - self._prev_disk.write_bytes) / dt
                    disk_delta = (read_s, write_s)
                self._prev_disk = dk
            except Exception:
                pass

            # Net I/O delta
            net_delta = (None, None)
            try:
                nt = _psutil.net_io_counters()
                if nt and self._prev_net and self._prev_ts:
                    dt = max(now - self._prev_ts, 0.001)
                    recv_s = (nt.bytes_recv - self._prev_net.bytes_recv) / dt
                    sent_s = (nt.bytes_sent - self._prev_net.bytes_sent) / dt
                    net_delta = (recv_s, sent_s)
                self._prev_net = nt
            except Exception:
                pass

            self._prev_ts = now

            self.after(0, lambda: self._update_ui(
                cpu, vm, proc_cpu, proc_mem, procs, disk_delta, net_delta
            ))
        except Exception:
            pass
        self.after(self._POLL_MS, self._poll)

    def _update_ui(
        self,
        cpu: float,
        vm,
        proc_cpu: float,
        proc_mem: float,
        procs: list[tuple[int, float, float, str]],
        disk_delta: tuple,
        net_delta: tuple,
    ) -> None:
        if not _PSUTIL:
            return

        self._cpu_bar.update(cpu, f"{cpu:.0f}%")
        self._cpu_spark.push(cpu)

        ram_pct   = vm.percent
        ram_used  = vm.used  / 1024 ** 3
        ram_total = vm.total / 1024 ** 3
        self._ram_bar.update(ram_pct, f"{ram_used:.1f} / {ram_total:.1f} GB")
        self._ram_spark.push(ram_pct)

        warnings: list[str] = []
        if cpu >= 85:
            warnings.append(f"CPU {cpu:.0f}%")
        if ram_pct >= 85:
            warnings.append(f"RAM {ram_pct:.0f}%")
        warn_text = "  ·  ".join(warnings)
        self._proc_lbl.configure(
            text=f"This process — CPU: {proc_cpu:.1f}%   RAM: {proc_mem:.0f} MB"
            + (f"   ⚠ {warn_text}" if warn_text else ""),
            text_color=T.STATUS_ERROR if warnings else T.TEXT_SECONDARY,
        )

        self._top_table.set_data(procs)
        self._refresh_lbl.configure(text=f"Updated {time.strftime('%H:%M:%S')}")

        # Disk
        read_s, write_s = disk_delta
        if read_s is not None:
            self._disk_tile.update(_human_bytes(read_s), _human_bytes(write_s))

        # Net
        recv_s, sent_s = net_delta
        if recv_s is not None:
            self._net_tile.update(_human_bytes(recv_s), _human_bytes(sent_s))

    def apply_system_snapshot(self, snapshot) -> None:
        """Update meters from the architecture's SystemSnapshot event."""
        cpu = float(getattr(snapshot, "cpu_percent", 0.0))
        ram = float(getattr(snapshot, "ram_percent", 0.0))
        self._cpu_bar.update(cpu, f"{cpu:.0f}%")
        self._cpu_spark.push(cpu)
        self._ram_bar.update(ram, f"{ram:.0f}%")
        self._ram_spark.push(ram)
        phase = str(getattr(snapshot, "phase", "idle"))
        self._proc_lbl.configure(
            text=f"System phase: {phase.title()}  ·  Source: SystemSnapshot"
        )

    def push_service_state(self, service: str, state: str) -> None:
        """Record a service state tick on the health timeline."""
        self._service_timeline.push_service_state(service, state)

    def push_tool_event(self, text: str, is_error: bool = False) -> None:
        """Append a tool run entry. Called from app.py via UIQueue."""
        color = T.STATUS_ERROR if is_error else T.STATUS_READY
        self._tool_log.push(text, color)

    def load_errors(self, errors: tuple[str, ...]) -> None:
        """Sync error log from AppState.errors. Called from _apply_catalog_views."""
        self._error_log.load_errors(errors)

    def on_hide(self) -> None:
        self._active = False

    def on_show(self) -> None:
        if not self._active:
            self._active = True
            self._poll()
