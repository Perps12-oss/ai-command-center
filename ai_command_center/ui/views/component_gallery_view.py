"""Component library gallery — documents design-system tokens and components."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.components.glass_card import GlassCard
from ai_command_center.ui.design_system import theme_v2 as T


class ComponentGalleryView(ctk.CTkScrollableFrame):
    """Visual catalog of design-system tokens and reusable components."""

    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self,
            text="Component Gallery",
            font=T.FONT_TITLE,
            text_color=T.TEXT_HEADING,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 8))

        ctk.CTkLabel(
            self,
            text="Design-system tokens and reusable UI primitives.",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", padx=T.PAD, pady=(0, 8))

        self._section("Colors")
        self._color_swatches(
            [
                ("BG Deep", T.BG_DEEP),
                ("BG Panel", T.BG_PANEL),
                ("BG Glass", T.BG_GLASS),
                ("Accent", T.ACCENT_DEFAULT),
                ("Text Primary", T.TEXT_PRIMARY),
                ("Text Secondary", T.TEXT_SECONDARY),
                ("Text Muted", T.TEXT_MUTED),
                ("Status Ready", T.STATUS_READY),
                ("Status Busy", T.STATUS_BUSY),
                ("Status Error", T.STATUS_ERROR),
            ]
        )

        self._section("Typography")
        self._type_row("Title", T.FONT_TITLE)
        self._type_row("Header", T.FONT_HEADER)
        self._type_row("Body", T.FONT_BODY)
        self._type_row("Small", T.FONT_SMALL)
        self._type_row("Mono", T.FONT_MONO)

        self._section("Radii")
        self._radius_row("Corner", T.CORNER_RADIUS)
        self._radius_row("Small", T.SMALL_RADIUS)
        self._radius_row("Pill", T.PILL_RADIUS)
        self._radius_row("Bubble", T.BUBBLE_RADIUS)

        self._section("Components")
        self._component_card()

    def _section(self, title: str) -> None:
        ctk.CTkLabel(
            self,
            text=title,
            font=T.FONT_HEADER,
            text_color=T.TEXT_LABEL,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 8))

    def _color_swatches(self, colors: list[tuple[str, str]]) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=T.PAD, pady=(0, 8))
        for name, color in colors:
            cell = ctk.CTkFrame(row, fg_color="transparent")
            cell.pack(side="left", padx=8, pady=4)
            swatch = ctk.CTkFrame(
                cell,
                width=40,
                height=40,
                fg_color=color,
                corner_radius=T.CORNER_RADIUS,
                border_width=1,
                border_color=T.BG_GLASS_BORDER,
            )
            swatch.pack()
            ctk.CTkLabel(
                cell,
                text=name,
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
            ).pack()

    def _type_row(self, name: str, font) -> None:
        ctk.CTkLabel(
            self,
            text=f"{name}: The quick brown fox",
            font=font,
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w", padx=T.PAD, pady=(0, 4))

    def _radius_row(self, name: str, radius: int) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=T.PAD, pady=(0, 8))
        ctk.CTkFrame(
            row,
            width=40,
            height=40,
            fg_color=T.ACCENT_DEFAULT,
            corner_radius=radius,
        ).pack(side="left")
        ctk.CTkLabel(
            row,
            text=f"{name} ({radius}px)",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
        ).pack(side="left", padx=(12, 0))

    def _component_card(self) -> None:
        card = GlassCard(self)
        card.pack(fill="x", padx=T.PAD, pady=(0, 8))
        ctk.CTkLabel(
            card,
            text="GlassCard",
            font=T.FONT_HEADER,
            text_color=T.TEXT_PRIMARY,
        ).pack(anchor="w", padx=T.PAD, pady=(T.PAD, 4))
        ctk.CTkLabel(
            card,
            text="Container with glass styling and default padding.",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
        ).pack(anchor="w", padx=T.PAD, pady=(0, T.PAD))
        ctk.CTkButton(
            card,
            text="Primary Button",
            font=T.FONT_SMALL,
            corner_radius=T.SMALL_RADIUS,
        ).pack(anchor="w", padx=T.PAD, pady=(0, T.PAD))
