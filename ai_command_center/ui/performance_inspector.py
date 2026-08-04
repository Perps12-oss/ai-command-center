"""Performance Inspector — read-only EventBus / AppState / SQLite timings."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.perf.metrics import get_perf_metrics
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.ui_queue import UIQueue


class PerformanceInspector(ctk.CTkToplevel):
    """Developer inspector showing why the app is slow (targets from perf architecture)."""

    WIDTH = 720
    HEIGHT = 560

    def __init__(
        self,
        master: ctk.CTk,
        bus: EventBus,
        state_store: AppStateStore,
        *,
        ui_queue: UIQueue,
    ) -> None:
        super().__init__(master)
        self._bus = bus
        self._state_store = state_store
        self._ui_queue = ui_queue
        self._refresh_pending = False

        self.title("Performance Inspector (dev)")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.configure(fg_color=("#f0f0f0", "#141414"))

        ctk.CTkLabel(
            self,
            text="Performance Inspector",
            font=T.FONT_TITLE,
            text_color=T.TEXT_HEADING,
        ).pack(pady=(12, 4))
        ctk.CTkLabel(
            self,
            text="Targets: UI <16ms · navigate <10ms · publish sync <2ms · telemetry async",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack()

        self._text = ctk.CTkTextbox(self, font=("Consolas", 11))
        self._text.pack(fill="both", expand=True, padx=12, pady=12)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(pady=(0, 12))
        ctk.CTkButton(row, text="Refresh", command=self._schedule_refresh).pack(
            side="left", padx=4
        )

        self._unsub = self._state_store.subscribe(lambda _s: self._schedule_refresh())
        self._schedule_refresh()
        self.after(1000, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.transient(master)
        self.focus_set()

    def _tick(self) -> None:
        if not self.winfo_exists():
            return
        self._schedule_refresh()
        self.after(1000, self._tick)

    def _schedule_refresh(self) -> None:
        if self._refresh_pending:
            return
        self._refresh_pending = True
        self._ui_queue.enqueue(self._refresh)

    def _refresh(self) -> None:
        self._refresh_pending = False
        metrics = get_perf_metrics().snapshot()
        bus_metrics = self._bus.get_handler_metrics()
        topic_counts = self._bus.get_topic_counts()
        top_topics = sorted(topic_counts.items(), key=lambda kv: -kv[1])[:12]
        timings = metrics.get("timings") or {}
        counters = metrics.get("counters") or {}

        lines = [
            f"uptime_s: {metrics.get('uptime_s')}",
            f"eventbus queue_depth: {bus_metrics.get('queue_depth')}",
            f"eventbus dropped: {bus_metrics.get('dropped_events')}",
            f"eventbus handler_invocations: {bus_metrics.get('handler_invocations')}",
            f"eventbus handler_avg_ms: {bus_metrics.get('handler_duration_avg_ms'):.3f}",
            f"navigate_reentrant_drops: {getattr(self._bus, '_navigate_dropped_reentrant', 0)}",
            "",
            "Timing samples (avg / max / last ms):",
        ]
        for name in sorted(timings):
            t = timings[name]
            lines.append(
                f"  {name}: avg={t['avg_ms']:.2f} max={t['max_ms']:.2f} "
                f"last={t['last_ms']:.2f} n={int(t['n'])}"
            )
        lines.append("")
        lines.append("Counters:")
        for name in sorted(counters):
            lines.append(f"  {name}: {counters[name]}")
        lines.append("")
        lines.append("Top publish counts:")
        for topic, count in top_topics:
            lines.append(f"  {topic}: {count}")
        lines.append("")
        lines.append("Budget targets:")
        lines.append("  ui.apply_state < 16ms / <2ms (e2e phase1→phase3)")
        lines.append("  ui.apply_state.phase3 < 16ms (visible view + lifecycle)")
        lines.append("  ui.apply_state.stream < 4ms")
        lines.append("  appstate.reduce < 0.5ms (constitution) / <2ms CI")
        lines.append("  appstate.notify < 1ms (listener fan-out; PERF-001)")
        lines.append("  chat.chunk coalesce 40ms (APPSTATE_NOTIFY_COALESCE_MS)")
        lines.append("  sqlite.telemetry_batch (async worker only)")

        content = "\n".join(lines)
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", content)
        self._text.configure(state="disabled")

    def _on_close(self) -> None:
        try:
            self._unsub()
        except Exception:
            pass
        self.destroy()
