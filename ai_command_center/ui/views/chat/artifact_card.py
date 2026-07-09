"""ArtifactCard — inline artifact preview card for the message feed.

Displays a compact artifact tile with kind icon, label, and action buttons.
Publishes ui.artifact.action via on_action callback.

Architecture contract: pure display widget, no bus/service imports.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T

_KIND_ICONS: dict[str, str] = {
    "text":     "📄",
    "code":     "⌥",
    "image":    "🖼",
    "pdf":      "📕",
    "email":    "✉",
    "calendar": "📅",
    "data":     "📊",
    "markdown": "✦",
}

_KIND_COLORS: dict[str, str] = {
    "text":     T.TEXT_SECONDARY,
    "code":     T.CODE_TEXT,
    "image":    "#A78BFA",
    "pdf":      "#F87171",
    "email":    T.ACCENT_DEFAULT,
    "calendar": T.STATUS_READY,
    "data":     T.STATUS_BUSY,
    "markdown": T.TEXT_PRIMARY,
}


class ArtifactCard(ctk.CTkFrame):
    """Compact artifact tile shown below assistant messages.

    ┌─────────────────────────────────────┐
    │ 📄  artifact label            ⤢  ⬇  │
    │    text · 2.1 KB                    │
    └─────────────────────────────────────┘
    """

    def __init__(
        self,
        master: Any,
        artifact_id: str,
        kind: str,
        label: str,
        *,
        size_bytes: int = 0,
        preview_snippet: str = "",
        on_action: Callable[[str, str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        color = _KIND_COLORS.get(kind, T.TEXT_SECONDARY)
        super().__init__(
            master,
            fg_color=T.BG_GLASS,
            corner_radius=T.SMALL_RADIUS,
            border_width=1,
            border_color=T.BG_GLASS_BORDER,
            **kwargs,
        )
        self._artifact_id = artifact_id
        self._on_action = on_action or (lambda a, k: None)
        icon = _KIND_ICONS.get(kind, "📄")

        # Main row
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)

        ctk.CTkLabel(
            row,
            text=icon,
            font=(T.FONT_FAMILY, 14),
            text_color=color,
            width=24,
        ).pack(side="left")

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=(4, 0))

        ctk.CTkLabel(
            info,
            text=label or artifact_id[:32],
            font=(T.FONT_FAMILY, 11),
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        sub_parts = [kind]
        if size_bytes:
            if size_bytes >= 1024:
                sub_parts.append(f"{size_bytes / 1024:.1f} KB")
            else:
                sub_parts.append(f"{size_bytes} B")

        ctk.CTkLabel(
            info,
            text=" · ".join(sub_parts),
            font=(T.FONT_FAMILY, 9),
            text_color=T.TEXT_MUTED,
            anchor="w",
        ).pack(anchor="w")

        snippet = (preview_snippet or "").strip()
        if snippet:
            ctk.CTkLabel(
                info,
                text=snippet,
                font=(T.FONT_FAMILY, 9),
                text_color=T.TEXT_SECONDARY,
                anchor="w",
                wraplength=360,
                justify="left",
            ).pack(anchor="w", pady=(2, 0))

        # Action buttons
        btn_cfg: dict[str, Any] = dict(
            width=22, height=22,
            font=(T.FONT_FAMILY, 10),
            fg_color="transparent",
            hover_color=T.BG_GLASS_BORDER,
            text_color=T.TEXT_MUTED,
            corner_radius=4,
        )
        ctk.CTkButton(
            row, text="⤢",
            command=lambda: self._on_action(self._artifact_id, "preview"),
            **btn_cfg,
        ).pack(side="right", padx=2)
        ctk.CTkButton(
            row, text="⬇",
            command=lambda: self._on_action(self._artifact_id, "download"),
            **btn_cfg,
        ).pack(side="right", padx=2)
