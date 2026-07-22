"""Brain UI card helpers — pure projection widgets."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class GoalCard(ctk.CTkFrame):
    """Compact brain goal row."""

    def __init__(
        self,
        master: Any,
        *,
        goal_id: str,
        text: str,
        status: str,
        priority: int = 0,
        on_select: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.GOAL_AMBER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
            **kwargs,
        )
        self._goal_id = goal_id
        self._on_select = on_select
        ctk.CTkLabel(
            self,
            text=text or goal_id or "Goal",
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
            wraplength=420,
        ).pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(
            self,
            text=f"{status} · priority {priority}",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 8))
        self.bind("<Button-1>", self._click)

    def _click(self, _e: Any = None) -> None:
        if self._on_select is not None and self._goal_id:
            self._on_select(self._goal_id)


class ObservationCard(ctk.CTkFrame):
    """Compact observation row."""

    def __init__(
        self,
        master: Any,
        *,
        content: str,
        source: str = "",
        confidence: float = 1.0,
        on_select: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
            **kwargs,
        )
        self._on_select = on_select
        ctk.CTkLabel(
            self,
            text=content or "(empty observation)",
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
            wraplength=420,
        ).pack(fill="x", padx=10, pady=(8, 2))
        meta = source or "unknown source"
        ctk.CTkLabel(
            self,
            text=f"{meta} · conf {confidence:.2f}",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 8))
        self.bind("<Button-1>", lambda _e: on_select() if on_select else None)


class ActionCard(ctk.CTkFrame):
    """Compact runtime action row."""

    def __init__(
        self,
        master: Any,
        *,
        action_type: str,
        status: str,
        result: str = "",
        error: str = "",
        on_select: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.BG_GLASS_BORDER,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
            **kwargs,
        )
        title = action_type or "action"
        ctk.CTkLabel(
            self,
            text=f"{title} · {status}",
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 2))
        detail = error or result or ""
        if detail:
            ctk.CTkLabel(
                self,
                text=detail[:200],
                font=(T.FONT_FAMILY, 10),
                text_color=T.STATUS_ERROR if error else T.TEXT_MUTED,
                anchor="w",
                wraplength=420,
            ).pack(fill="x", padx=10, pady=(0, 8))
        else:
            ctk.CTkFrame(self, height=4, fg_color="transparent").pack()
        self.bind("<Button-1>", lambda _e: on_select() if on_select else None)


class PlanCard(ctk.CTkFrame):
    """Current plan summary with steps."""

    def __init__(
        self,
        master: Any,
        *,
        plan_id: str = "",
        goal: str = "",
        status: str = "",
        steps: tuple[tuple[str, str], ...] = (),
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            border_color=T.ACCENT_DEFAULT,
            border_width=1,
            corner_radius=T.SMALL_RADIUS,
            **kwargs,
        )
        header = goal or plan_id or "No active plan"
        ctk.CTkLabel(
            self,
            text=header,
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
            wraplength=420,
        ).pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(
            self,
            text=f"status: {status or 'n/a'} · {len(steps)} step(s)",
            font=(T.FONT_FAMILY, 10),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 4))
        for desc, step_status in steps[:8]:
            ctk.CTkLabel(
                self,
                text=f"• [{step_status}] {desc}",
                font=(T.FONT_FAMILY, 10),
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                wraplength=400,
            ).pack(fill="x", padx=14, pady=1)
        ctk.CTkFrame(self, height=8, fg_color="transparent").pack()


__all__ = ["GoalCard", "ObservationCard", "ActionCard", "PlanCard"]
