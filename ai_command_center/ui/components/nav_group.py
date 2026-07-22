"""Collapsible navigation group for the Sidebar."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class NavGroup(ctk.CTkFrame):
    """A titled, collapsible group of sidebar navigation buttons."""

    def __init__(
        self,
        master: ctk.CTkFrame,
        title: str,
        items: Sequence[tuple[str, str]],
        on_select: Callable[[str], None],
        initially_expanded: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", border_width=0, corner_radius=0, **kwargs)

        self._title = title
        self._items = list(items)
        self._on_select = on_select
        self._expanded = initially_expanded
        self._compact = False
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._active_id: str | None = None

        self._header = ctk.CTkButton(
            self,
            text=self._header_text(),
            anchor="w",
            font=T.FONT_ROLE,
            text_color=T.TEXT_MUTED,
            fg_color="transparent",
            hover_color=T.LIGHT_GLASS,
            height=24,
            corner_radius=T.CORNER_RADIUS,
            command=self.toggle,
        )
        self._header.pack(fill="x", padx=T.PAD + 2, pady=(8, 4))

        self._content = ctk.CTkFrame(self, fg_color="transparent", border_width=0, corner_radius=0)
        if self._expanded:
            self._content.pack(fill="x")

        for view_id, label in self._items:
            row = ctk.CTkFrame(self._content, fg_color="transparent", height=40)
            row.pack(fill="x", padx=8, pady=2)
            row.pack_propagate(False)

            btn = ctk.CTkButton(
                row,
                text=label,
                anchor="w",
                font=T.FONT_BODY,
                fg_color="transparent",
                text_color=T.TEXT_SECONDARY,
                hover_color=T.LIGHT_GLASS,
                height=36,
                corner_radius=T.CORNER_RADIUS,
                command=lambda v=view_id: self._select(v),
            )
            btn.pack(fill="both", expand=True, padx=4)
            self._buttons[view_id] = btn

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @property
    def buttons(self) -> dict[str, ctk.CTkButton]:
        return self._buttons

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    def toggle(self) -> None:
        """Toggle visibility of the group's items."""
        self._expanded = not self._expanded
        if self._expanded:
            self._content.pack(fill="x")
        else:
            self._content.pack_forget()
        self._header.configure(text=self._header_text())

    def set_expanded(self, expanded: bool) -> None:
        """Programmatically expand or collapse the group."""
        if expanded != self._expanded:
            self.toggle()

    def set_active(self, view_id: str) -> None:
        """Highlight the active view button; clear others."""
        self._active_id = view_id
        for vid, btn in self._buttons.items():
            if vid == view_id:
                btn.configure(
                    fg_color=T.HERO_CYAN_DIM,
                    text_color=T.HERO_CYAN,
                    border_width=0,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=T.TEXT_SECONDARY,
                    border_width=0,
                )

    def set_compact(self, compact: bool) -> None:
        """Switch between full-label and icon-only (no text) sidebar mode."""
        self._compact = compact
        self._header.configure(text="" if compact else self._header_text())
        for vid, btn in self._buttons.items():
            label = dict(self._items).get(vid, vid)
            btn.configure(text="" if compact else label)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _header_text(self) -> str:
        chevron = "▼" if self._expanded else "▶"
        return f"{chevron}  {self._title.upper()}"

    def _select(self, view_id: str) -> None:
        self.set_active(view_id)
        self._on_select(view_id)
