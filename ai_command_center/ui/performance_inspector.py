"""Performance Inspector — read-only EventBus / AppState / SQLite timings."""

from __future__ import annotations

import time

import customtkinter as ctk

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.perf.metrics import get_perf_metrics
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.inspector_refresh import record_inspector_refresh
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
        self._last_fingerprint: tuple | None = None

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

        # PERF-002: metrics live in PerfMetrics / EventBus — do not fan out on
        # AppState notifies (timer + manual Refresh are sufficient).
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

    @staticmethod
    def _fingerprint(
        *,
        uptime_s: object,
        bus_metrics: dict,
        navigate_dropped: int,
        timings: dict,
        counters: dict,
        top_topics: list[tuple[str, int]],
    ) -> tuple:
        """Stable display fingerprint (excludes nothing the dump shows)."""
        timing_fp = tuple(
            (
                name,
                round(float(t.get("avg_ms", 0.0)), 2),
                round(float(t.get("max_ms", 0.0)), 2),
                round(float(t.get("last_ms", 0.0)), 2),
                int(t.get("n", 0)),
            )
            for name, t in sorted(timings.items())
        )
        counter_fp = tuple(sorted((k, int(v)) for k, v in counters.items()))
        return (
            uptime_s,
            bus_metrics.get("queue_depth"),
            bus_metrics.get("dropped_events"),
            bus_metrics.get("handler_invocations"),
            round(float(bus_metrics.get("handler_duration_avg_ms") or 0.0), 3),
            navigate_dropped,
            timing_fp,
            counter_fp,
            tuple(top_topics),
        )

    def _refresh(self) -> None:
        self._refresh_pending = False
        started = time.perf_counter()
        metrics = get_perf_metrics().snapshot()
        bus_metrics = self._bus.get_handler_metrics()
        topic_counts = self._bus.get_topic_counts()
        top_topics = sorted(topic_counts.items(), key=lambda kv: -kv[1])[:12]
        timings = metrics.get("timings") or {}
        counters = metrics.get("counters") or {}
        navigate_dropped = int(getattr(self._bus, "_navigate_dropped_reentrant", 0))

        fp = self._fingerprint(
            uptime_s=metrics.get("uptime_s"),
            bus_metrics=bus_metrics,
            navigate_dropped=navigate_dropped,
            timings=timings,  # type: ignore[arg-type]
            counters=counters,  # type: ignore[arg-type]
            top_topics=top_topics,
        )
        if fp == self._last_fingerprint:
            record_inspector_refresh("performance", 0.0, skipped=True)
            return
        self._last_fingerprint = fp

        lines = [
            f"uptime_s: {metrics.get('uptime_s')}",
            f"eventbus queue_depth: {bus_metrics.get('queue_depth')}",
            f"eventbus dropped: {bus_metrics.get('dropped_events')}",
            f"eventbus handler_invocations: {bus_metrics.get('handler_invocations')}",
            f"eventbus handler_avg_ms: {bus_metrics.get('handler_duration_avg_ms'):.3f}",
            f"navigate_reentrant_drops: {navigate_dropped}",
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
        lines.append("  inspector.refresh < 5ms (PERF-002)")
        lines.append("  sqlite.telemetry_batch (async worker only)")

        content = "\n".join(lines)
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", content)
        self._text.configure(state="disabled")
        record_inspector_refresh(
            "performance", (time.perf_counter() - started) * 1000.0
        )

    def _on_close(self) -> None:
        self.destroy()
