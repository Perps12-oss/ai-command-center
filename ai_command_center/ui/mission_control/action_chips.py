"""Interactive action chips — pre-fill the command palette / command box."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


CHIP_SPECS: tuple[tuple[str, str, str], ...] = (
    ("Ask AI", "What can you help me with today?", T.ACCENT_DEFAULT),
    ("Shell", "> ", T.TEXT_SECONDARY),
    ("Remember", "remember: | ", T.GOAL_AMBER),
    ("Clipboard", "summarize clipboard", T.WORLD_TEAL),
    ("Notes", "note: ", T.EXECUTION_BLUE),
    ("New Goal", "goal: ", T.APPROVAL_ORANGE),
)


class ActionChips(ctk.CTkFrame):
    """Row of chips that pre-fill the global command surface on click."""

    def __init__(
        self,
        master,
        *,
        on_chip: Callable[[str], None] | None = None,
        chips: tuple[tuple[str, str, str], ...] = CHIP_SPECS,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_chip = on_chip
        self._buttons: list[ctk.CTkButton] = []

        for label, payload, color in chips:
            btn = ctk.CTkButton(
                self,
                text=label,
                font=T.FONT_SMALL,
                height=26,
                width=84,
                corner_radius=T.PILL_RADIUS,
                fg_color=T.BG_GLASS,
                hover_color=T.LIGHT_GLASS,
                text_color=color,
                border_width=1,
                border_color=T.GLASS_BORDER,
                command=lambda p=payload: self._fire(p),
            )
            btn.pack(side="left", padx=(0, 6))
            self._buttons.append(btn)

    def _fire(self, payload: str) -> None:
        if self._on_chip is not None:
            self._on_chip(payload)
