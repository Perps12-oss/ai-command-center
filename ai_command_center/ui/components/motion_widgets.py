"""Motion primitives — EventBus-driven live widgets."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.floating_ui import floating_scroll
from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.theme import tokens as T


class ActivityPulse(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._dots: list[ctk.CTkLabel] = []
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=T.PAD, pady=4)
        for _ in range(5):
            dot = ctk.CTkLabel(row, text="●", font=T.FONT_SMALL, text_color=T.TEXT_MUTED)
            dot.pack(side="left", padx=4)
            self._dots.append(dot)

    def set_intensity(self, intensity: float) -> None:
        for i, dot in enumerate(self._dots):
            on = intensity > (i + 1) / len(self._dots)
            dot.configure(text_color=T.ACCENT_PRIMARY if on else T.TEXT_MUTED)


class StatusFluxBar(ctk.CTkFrame):
    def __init__(self, master, label: str, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(
            self, text=label, font=T.FONT_SMALL, text_color=T.TEXT_SECONDARY, width=90, anchor="w"
        ).pack(side="left")
        self._bar = ctk.CTkProgressBar(
            self, height=8, progress_color=T.ACCENT_PRIMARY, fg_color=T.BG_INPUT
        )
        self._bar.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._bar.set(0)

    def set_value(self, percent: float) -> None:
        self._bar.set(max(0.0, min(1.0, percent / 100.0)))


class SystemHeartbeat(GlassCard):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        ctk.CTkLabel(
            self,
            text="System Heartbeat",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 4))
        self._pulse = ActivityPulse(self)
        self._pulse.pack(fill="x")

    def set_rate(self, intensity: float) -> None:
        self._pulse.set_intensity(intensity)


class StatusFluxBarGrid(GlassCard):
    def __init__(self, master, metrics: tuple[str, ...] = ("CPU", "RAM", "MODEL_LOAD", "NETWORK"), **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._bars: dict[str, StatusFluxBar] = {}
        for name in metrics:
            bar = StatusFluxBar(self, name)
            bar.pack(fill="x", padx=T.PAD, pady=4)
            self._bars[name] = bar
        ctk.CTkFrame(self, height=8, fg_color="transparent").pack()

    def update_values(self, values: dict[str, float]) -> None:
        key_map = {
            "CPU": "cpu_percent",
            "RAM": "ram_percent",
            "MODEL_LOAD": "model_load",
            "NETWORK": "network",
        }
        for label, bar in self._bars.items():
            key = key_map.get(label, label.lower())
            bar.set_value(float(values.get(key, values.get(label, 0))))


class EventStreamRibbon(GlassCard):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        ctk.CTkLabel(
            self,
            text="Event Stream",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 4))
        self._scroll = floating_scroll(self, height=100)
        self._scroll.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

    def push_event(self, detail: str) -> None:
        row = ctk.CTkLabel(
            self._scroll,
            text=f"› {detail}",
            font=T.FONT_MONO,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        row.pack(fill="x", pady=1)
        children = self._scroll.winfo_children()
        if len(children) > 30:
            children[0].destroy()


class CommandFlowTrail(GlassCard):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        ctk.CTkLabel(
            self,
            text="Command Flow",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 4))
        self._scroll = floating_scroll(self, height=100)
        self._scroll.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

    def push_command(self, text: str) -> None:
        row = ctk.CTkLabel(
            self._scroll,
            text=f"$ {text}",
            font=T.FONT_MONO,
            text_color=T.ACCENT_PRIMARY,
            anchor="w",
        )
        row.pack(fill="x", pady=1)
        children = self._scroll.winfo_children()
        if len(children) > 20:
            children[0].destroy()


class ActivityPulseField(GlassCard):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        ctk.CTkLabel(
            self,
            text="Activity Field",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 4))
        self._pulse = ActivityPulse(self)
        self._pulse.pack(fill="x", padx=T.PAD, pady=(0, T.PAD))

    def set_density(self, intensity: float) -> None:
        self._pulse.set_intensity(intensity)


class LiveSurfaceLayer(ctk.CTkFrame):
    """Thin motion band under hero."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", height=28, **kwargs)
        self.pack_propagate(False)
        self._pulse = ActivityPulse(self)
        self._pulse.pack(fill="x", padx=T.PAD)

    def set_intensity(self, intensity: float) -> None:
        self._pulse.set_intensity(intensity)
