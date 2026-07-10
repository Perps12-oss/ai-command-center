"""KeyboardShortcutsOverlay — modal overlay showing available keyboard shortcuts.

P4.6: Keyboard shortcuts overlay
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

__all__ = ["KeyboardShortcutsOverlay", "ShortcutsOverlayManager", "SHORTCUTS"]


# Define keyboard shortcuts
SHORTCUTS = [
    {"category": "Selection", "shortcuts": [
        {"keys": "Click", "description": "Select node/edge"},
        {"keys": "Ctrl + Click", "description": "Add to selection"},
        {"keys": "Shift + Drag", "description": "Box select"},
        {"keys": "Ctrl + A", "description": "Select all"},
        {"keys": "Escape", "description": "Clear selection"},
    ]},
    {"category": "Editing", "shortcuts": [
        {"keys": "Drag node", "description": "Move node"},
        {"keys": "Drag edge handle", "description": "Create edge"},
        {"keys": "Delete", "description": "Delete selected"},
        {"keys": "Double-click edge", "description": "Delete edge"},
        {"keys": "Right-click", "description": "Context menu"},
    ]},
    {"category": "History", "shortcuts": [
        {"keys": "Ctrl + Z", "description": "Undo"},
        {"keys": "Ctrl + Y", "description": "Redo"},
        {"keys": "Ctrl + Shift + Z", "description": "Redo (alt)"},
    ]},
    {"category": "View", "shortcuts": [
        {"keys": "Mouse Wheel", "description": "Zoom in/out"},
        {"keys": "Middle Mouse + Drag", "description": "Pan canvas"},
        {"keys": "Ctrl + 0", "description": "Reset zoom"},
        {"keys": "Ctrl + =", "description": "Zoom in"},
        {"keys": "Ctrl + -", "description": "Zoom out"},
    ]},
    {"category": "Workflow", "shortcuts": [
        {"keys": "Space", "description": "Toggle run/pause"},
        {"keys": "Ctrl + Enter", "description": "Run workflow"},
        {"keys": "Ctrl + .", "description": "Stop workflow"},
    ]},
]


class KeyboardShortcutsOverlay(ctk.CTkFrame):
    """Modal overlay displaying available keyboard shortcuts."""

    def __init__(
        self,
        master: Any,
        on_close: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color=T.BG_PANEL, corner_radius=12, **kwargs)
        self._on_close = on_close or (lambda: None)

        # Semi-transparent backdrop
        self.configure(fg_color=(T.BG_PANEL, T.BG_DEEP))

        # Title bar
        title_bar = ctk.CTkFrame(self, fg_color="transparent", height=40)
        title_bar.pack(fill="x", padx=16, pady=(12, 8))

        title = ctk.CTkLabel(
            title_bar,
            text="⌨️ Keyboard Shortcuts",
            font=(T.FONT_FAMILY, 14, "bold"),
            text_color=T.TEXT_PRIMARY,
        )
        title.pack(side="left")

        close_btn = ctk.CTkButton(
            title_bar,
            text="✕",
            width=28,
            height=28,
            font=(T.FONT_FAMILY, 12),
            fg_color="transparent",
            hover_color=T.BG_GLASS,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=self._on_close,
        )
        close_btn.pack(side="right")

        # Shortcuts content
        content = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=T.BG_GLASS,
        )
        content.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        for category_group in SHORTCUTS:
            # Category header
            cat_label = ctk.CTkLabel(
                content,
                text=category_group["category"],
                font=(T.FONT_FAMILY, 11, "bold"),
                text_color=T.ACCENT_DEFAULT,
            )
            cat_label.pack(anchor="w", pady=(12, 4))

            # Shortcuts in category
            for shortcut in category_group["shortcuts"]:
                row = ctk.CTkFrame(content, fg_color="transparent")
                row.pack(fill="x", pady=2)

                # Key badge
                keys_label = ctk.CTkLabel(
                    row,
                    text=shortcut["keys"],
                    font=("Consolas", 10),
                    text_color=T.TEXT_PRIMARY,
                    fg_color=T.BG_INPUT,
                    corner_radius=4,
                    padx=8,
                    pady=4,
                )
                keys_label.pack(side="left", padx=(0, 12))

                # Description
                desc_label = ctk.CTkLabel(
                    row,
                    text=shortcut["description"],
                    font=(T.FONT_FAMILY, 10),
                    text_color=T.TEXT_MUTED,
                )
                desc_label.pack(side="left")

        # Footer hint
        footer = ctk.CTkLabel(
            self,
            text="Press Escape or click outside to close",
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
        )
        footer.pack(side="bottom", pady=8)


class ShortcutsOverlayManager:
    """Manages the keyboard shortcuts overlay with a toggle button."""

    def __init__(self, master: Any) -> None:
        self._master = master
        self._overlay: KeyboardShortcutsOverlay | None = None
        self._backdrop: ctk.CTkFrame | None = None

    def toggle(self) -> None:
        """Toggle the shortcuts overlay visibility."""
        if self._overlay is not None:
            self.hide()
        else:
            self.show()

    def show(self) -> None:
        """Show the shortcuts overlay."""
        if self._overlay is not None:
            return

        # Create backdrop
        self._backdrop = ctk.CTkFrame(
            self._master,
            fg_color=(T.BG_DEEP + "CC", T.BG_DEEP + "99"),  # Semi-transparent
            corner_radius=0,
        )
        self._backdrop.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._backdrop.bind("<Button-1>", lambda _: self.hide())
        self._backdrop.bind("<Escape>", lambda _: self.hide())

        # Create overlay
        self._overlay = KeyboardShortcutsOverlay(
            self._master,
            width=400,
            height=500,
            on_close=self.hide,
        )
        self._overlay.place(relx=0.5, rely=0.5, anchor="center")

    def hide(self) -> None:
        """Hide the shortcuts overlay."""
        if self._overlay is not None:
            self._overlay.destroy()
            self._overlay = None
        if self._backdrop is not None:
            self._backdrop.destroy()
            self._backdrop = None

    def is_visible(self) -> bool:
        """Check if overlay is visible."""
        return self._overlay is not None


__all__ = ["KeyboardShortcutsOverlay", "ShortcutsOverlayManager", "SHORTCUTS"]
