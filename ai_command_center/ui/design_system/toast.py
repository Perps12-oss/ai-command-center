"""Toast notification system — ToastManager stacks dismissible bubbles top-right."""
from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_KIND_COLOR = {
    "info":    T.ACCENT_DEFAULT,
    "success": T.STATUS_READY,
    "warning": T.STATUS_BUSY,
    "error":   T.STATUS_ERROR,
}
_KIND_ICON = {
    "info":    "◈",
    "success": "●",
    "warning": "◔",
    "error":   "✕",
}


class _ToastBubble(ctk.CTkFrame):
    def __init__(self, master, message: str, kind: str, on_dismiss) -> None:
        color = _KIND_COLOR.get(kind, T.ACCENT_DEFAULT)
        super().__init__(
            master,
            fg_color=T.BG_PANEL,
            border_color=color,
            border_width=1,
            corner_radius=8,
            width=300,
        )
        self._on_dismiss = on_dismiss

        ctk.CTkFrame(self, width=3, fg_color=color, corner_radius=0).pack(
            side="left", fill="y"
        )

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=10, pady=8)

        ctk.CTkLabel(
            inner,
            text=f"{_KIND_ICON.get(kind, '◈')}  {message}",
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            wraplength=230,
            justify="left",
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            inner,
            text="✕",
            width=18,
            height=18,
            font=(T.FONT_FAMILY, 10),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
            command=self._dismiss,
        ).pack(side="right", padx=(4, 0))

    def schedule_dismiss(self, ms: int) -> None:
        self.after(ms, self._dismiss)

    def _dismiss(self) -> None:
        if self.winfo_exists():
            self._on_dismiss(self)


class ToastManager:
    """Manages stacked toast notifications anchored to the top-right of *master*."""

    def __init__(self, master) -> None:
        self._master = master
        self._toasts: list[_ToastBubble] = []

    def show(
        self,
        message: str,
        *,
        kind: str = "info",
        duration: int = 3000,
    ) -> None:
        toast = _ToastBubble(self._master, message, kind, self._dismiss)
        self._toasts.append(toast)
        self._reposition()
        toast.schedule_dismiss(duration)

    def _dismiss(self, toast: _ToastBubble) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        try:
            toast.place_forget()
            toast.destroy()
        except Exception:
            pass
        self._reposition()

    def _reposition(self) -> None:
        y = T.TOP_BAR_HEIGHT + 8
        for t in self._toasts:
            t.place(relx=1.0, x=-12, y=y, anchor="ne")
            t.lift()
            try:
                t.update_idletasks()
                y += t.winfo_reqheight() + 6
            except Exception:
                y += 60
