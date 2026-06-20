"""Floating layout helpers — transparent scroll hosts over wallpaper."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.theme import tokens as T

# Standard gap between floating glass cards and wallpaper.
FLOAT_PAD = T.PAD
FLOAT_GAP = T.GAP


def _transparentize_scroll(scroll: ctk.CTkScrollableFrame) -> None:
    """Strip painted slab from CTkScrollableFrame inner surfaces."""
    try:
        scroll._parent_canvas.configure(highlightthickness=0, bd=0)
        scroll._parent_frame.configure(border_width=0)
    except Exception:
        pass


def floating_scroll(master, *, height: int | None = None, **kwargs) -> ctk.CTkScrollableFrame:
    """
    Scroll host with no painted panel — only the scrollbar track, not a full-page slab.
    """
    opts = {
        "fg_color": "transparent",
        "bg_color": "transparent",
        "border_width": 0,
        "corner_radius": 0,
        "scrollbar_fg_color": "transparent",
        "scrollbar_button_color": T.GLASS_BORDER,
        "scrollbar_button_hover_color": T.GLASS_BORDER_HOVER,
    }
    opts.update(kwargs)
    scroll = ctk.CTkScrollableFrame(master, **opts)
    if height is not None:
        scroll.configure(height=height)
    _transparentize_scroll(scroll)
    return scroll


def pack_floating(
    widget,
    *,
    fill: str = "x",
    expand: bool = False,
    first: bool = False,
) -> None:
    """Pack a glass card with consistent floating margins."""
    top = FLOAT_PAD if first else 0
    widget.pack(
        fill=fill,
        expand=expand,
        padx=FLOAT_PAD,
        pady=(top, FLOAT_GAP),
    )
