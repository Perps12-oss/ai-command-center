"""Small CTk dialogs for Workspace OS entity creation."""

from __future__ import annotations

import customtkinter as ctk

from ai_command_center.ui.design_system import theme_v2 as T


class CreateWorkspaceDialog(ctk.CTkToplevel):
    """Title + optional description for a new workspace."""

    def __init__(self, master) -> None:
        super().__init__(master)
        self.title("Create Workspace")
        self.geometry("420x220")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.result: dict[str, str] | None = None

        ctk.CTkLabel(self, text="Title:", font=T.FONT_BODY).pack(anchor="w", padx=16, pady=(16, 0))
        self._title = ctk.CTkEntry(self, placeholder_text="Workspace name")
        self._title.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(self, text="Description (optional):", font=T.FONT_BODY).pack(
            anchor="w", padx=16, pady=(8, 0)
        )
        self._description = ctk.CTkEntry(self, placeholder_text="Short description")
        self._description.pack(fill="x", padx=16, pady=4)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(buttons, text="Create", command=self._create).pack(side="right", padx=4)
        ctk.CTkButton(buttons, text="Cancel", fg_color="transparent", command=self._cancel).pack(
            side="right", padx=4
        )

        self._title.focus_set()
        self._title.bind("<Return>", lambda _e: self._description.focus_set())
        self._description.bind("<Return>", lambda _e: self._create())

    def _create(self) -> None:
        title = self._title.get().strip()
        if title:
            self.result = {
                "title": title,
                "description": self._description.get().strip(),
            }
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class CreateCardDialog(ctk.CTkToplevel):
    """Create a card under a selected workspace."""

    def __init__(self, master, *, workspaces: list[tuple[str, str]]) -> None:
        super().__init__(master)
        self.title("Create Card")
        self.geometry("420x240")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.result: dict[str, str] | None = None
        self._workspaces = workspaces

        ctk.CTkLabel(self, text="Workspace:", font=T.FONT_BODY).pack(anchor="w", padx=16, pady=(16, 0))
        labels = [label for _id, label in workspaces]
        self._workspace = ctk.CTkOptionMenu(self, values=labels or ["— no workspaces —"])
        self._workspace.pack(fill="x", padx=16, pady=4)
        if not workspaces:
            self._workspace.configure(state="disabled")

        ctk.CTkLabel(self, text="Title:", font=T.FONT_BODY).pack(anchor="w", padx=16, pady=(8, 0))
        self._title = ctk.CTkEntry(self, placeholder_text="Card name")
        self._title.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(self, text="Description (optional):", font=T.FONT_BODY).pack(
            anchor="w", padx=16, pady=(8, 0)
        )
        self._description = ctk.CTkEntry(self)
        self._description.pack(fill="x", padx=16, pady=4)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(buttons, text="Create", command=self._create).pack(side="right", padx=4)
        ctk.CTkButton(buttons, text="Cancel", fg_color="transparent", command=self._cancel).pack(
            side="right", padx=4
        )
        self._title.focus_set()

    def _selected_workspace_id(self) -> str | None:
        if not self._workspaces:
            return None
        selected = self._workspace.get()
        for entity_id, label in self._workspaces:
            if label == selected:
                return entity_id
        return self._workspaces[0][0]

    def _create(self) -> None:
        title = self._title.get().strip()
        workspace_id = self._selected_workspace_id()
        if title and workspace_id:
            self.result = {
                "workspace_id": workspace_id,
                "title": title,
                "description": self._description.get().strip(),
            }
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class CreateResourceDialog(ctk.CTkToplevel):
    """Create a URL resource under a selected card."""

    def __init__(self, master, *, cards: list[tuple[str, str]]) -> None:
        super().__init__(master)
        self.title("Create Resource")
        self.geometry("420x280")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.result: dict[str, str] | None = None
        self._cards = cards

        ctk.CTkLabel(self, text="Card:", font=T.FONT_BODY).pack(anchor="w", padx=16, pady=(16, 0))
        labels = [label for _id, label in cards]
        self._card = ctk.CTkOptionMenu(self, values=labels or ["— no cards —"])
        self._card.pack(fill="x", padx=16, pady=4)
        if not cards:
            self._card.configure(state="disabled")

        ctk.CTkLabel(self, text="Title:", font=T.FONT_BODY).pack(anchor="w", padx=16, pady=(8, 0))
        self._title = ctk.CTkEntry(self, placeholder_text="Resource label")
        self._title.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(self, text="URL:", font=T.FONT_BODY).pack(anchor="w", padx=16, pady=(8, 0))
        self._url = ctk.CTkEntry(self, placeholder_text="https://...")
        self._url.pack(fill="x", padx=16, pady=4)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(buttons, text="Create", command=self._create).pack(side="right", padx=4)
        ctk.CTkButton(buttons, text="Cancel", fg_color="transparent", command=self._cancel).pack(
            side="right", padx=4
        )
        self._title.focus_set()

    def _selected_card_id(self) -> str | None:
        if not self._cards:
            return None
        selected = self._card.get()
        for entity_id, label in self._cards:
            if label == selected:
                return entity_id
        return self._cards[0][0]

    def _create(self) -> None:
        title = self._title.get().strip()
        url = self._url.get().strip()
        card_id = self._selected_card_id()
        if title and url and card_id:
            self.result = {
                "card_id": card_id,
                "title": title,
                "url": url,
            }
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
