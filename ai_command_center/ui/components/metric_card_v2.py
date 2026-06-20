"""Metric card v2 — glass surface + optional RingGauge / Sparkline viz slot."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.components.ring_gauge import RingGauge
from ai_command_center.ui.components.shadow_label import ShadowLabel
from ai_command_center.ui.components.sparkline import Sparkline
from ai_command_center.ui.components.status_pill import StatusPill
from ai_command_center.ui.theme import tokens as T


class MetricCardV2(GlassCard):
    def __init__(
        self,
        master,
        card_id: str,
        title: str,
        *,
        viz: str = "default",
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._card_id = card_id
        self._viz_type = viz

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=T.PAD, pady=(T.PAD, 4))

        self._title = ShadowLabel(header, text=title, anchor="w", height=22)
        self._title.pack(side="left", fill="x", expand=True)

        self._badge = StatusPill(header, "—", state="offline")
        self._badge.pack(side="right")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=T.PAD, pady=(0, T.PAD))

        self._value = ctk.CTkLabel(
            body,
            text="—",
            font=(T.FONT_FAMILY, 22, "bold"),
            text_color=T.TEXT_HEADING,
            anchor="w",
        )
        self._value.pack(fill="x")

        self._ring: RingGauge | None = None
        self._spark: Sparkline | None = None
        if viz == "ring":
            self._ring = RingGauge(body, size=64)
            self._ring.pack(anchor="w", pady=4)
        elif viz == "sparkline":
            self._spark = Sparkline(body, chart_width=180, chart_height=44)
            self._spark.pack(fill="x", pady=4)

        self._subtitle = ctk.CTkLabel(
            body,
            text="",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=220,
        )
        self._subtitle.pack(fill="x", pady=(4, 0))

    def update_metrics(
        self,
        *,
        value: str,
        badge_text: str = "—",
        badge_state: str = "ready",
        delta: float | None = None,
        percent: float | None = None,
        history: list[str] | None = None,
        subtitle: str | None = None,
    ) -> None:
        self._value.configure(text=value)
        self._badge.set_state(badge_text, badge_state)
        if self._ring is not None and percent is not None:
            self._ring.set_value(percent, label=f"{percent:.0f}%")
        if self._spark is not None:
            if percent is not None:
                self._spark.push(percent)
            elif history:
                nums = []
                for h in history:
                    try:
                        nums.append(float("".join(c for c in h if c.isdigit() or c == ".") or "0"))
                    except ValueError:
                        nums.append(float(len(nums) + 1))
                if nums:
                    self._spark.set_values(nums)
        parts: list[str] = []
        if delta is not None:
            arrow = "↑" if delta >= 0 else "↓"
            parts.append(f"{arrow} {abs(delta):.1f}%")
        if history:
            parts.append(" · ".join(history[:3]))
        if subtitle:
            parts.append(subtitle)
        self._subtitle.configure(text=" ".join(parts) if parts else "")


MetricCard = MetricCardV2
