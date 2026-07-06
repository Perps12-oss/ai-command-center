"""Window layout, visibility, and direct user interaction callbacks."""

from __future__ import annotations

import os
from collections.abc import Callable

import customtkinter as ctk

from ai_command_center.core.clipboard_intent import (
    empty_clipboard_message,
    wants_clipboard,
)
from ai_command_center.core.event_bus import Event
from ai_command_center.ui.capability_help import show_capability_help
from ai_command_center.ui.components.command_box import CommandBox
from ai_command_center.ui.components.command_history_drawer import CommandHistoryDrawer
from ai_command_center.ui.components.sidebar import Sidebar
from ai_command_center.ui.components.top_bar import TopBar
from ai_command_center.ui.design_system.command import CommandPalette
from ai_command_center.ui.design_system.shortcut import ShortcutOverlay
from ai_command_center.ui.design_system.toast import ToastManager
from ai_command_center.ui.design_system import theme_manager
from ai_command_center.ui.design_system import theme_v2 as T


class ApplicationShellMixin:
    """Builds the CTk shell and handles show/hide plus command input."""

    def _build_layout(self) -> None:
        self._top = TopBar(
            self,
            on_settings=lambda: self._navigate("settings"),
            on_close=self.hide,
        )
        self._top.pack(fill="x", side="top")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)

        self._sidebar = Sidebar(body, on_navigate=self._on_sidebar_navigate)
        self._sidebar.pack(fill="y", side="left")

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(fill="both", expand=True, side="left")

        self._command_host = ctk.CTkFrame(right, fg_color=T.BG_PANEL, corner_radius=0, height=80)
        self._command_host.pack(fill="x")
        self._command_host.pack_propagate(False)

        self._command_box = CommandBox(
            self._command_host,
            on_submit=self._on_command,
            on_help=self._show_capability_help,
        )
        self._command_box.pack(fill="x", padx=T.PAD, pady=10)

        self._content = ctk.CTkFrame(right, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

        self._show_view(self._default_view)

        self._toast = ToastManager(self)
        self._command_palette = CommandPalette(self)
        self._shortcut_overlay = ShortcutOverlay(self)

        self._history_drawer = CommandHistoryDrawer(
            body,
            on_rerun=self._on_command,
        )

    def _setup_keybindings(self) -> None:
        self.bind("<Control-k>", lambda _: self._show_command_palette())
        self.bind("<Control-K>", lambda _: self._show_command_palette())
        self.bind("<Control-h>", lambda _: self._history_drawer.toggle())
        self.bind("<Control-H>", lambda _: self._history_drawer.toggle())
        self.bind("?", self._maybe_show_shortcuts)

    def _show_command_palette(self) -> None:
        commands: list[tuple[str, str, Callable[[], None]]] = []
        commands.extend(self._workspace_os_palette_commands())
        commands.extend(
            [
                ("◈  Workspace", "Entity canvas — workspaces, cards, resources", lambda: self._navigate("workspace")),
                ("⌂  Home", "Dashboard and quick actions", lambda: self._navigate("home")),
                ("💬  Chat", "Generic chat (no entity attach)", lambda: self._navigate("chat", clear_chat_entity=True)),
                ("📝  Notes", "Search vault notes", lambda: self._navigate("notes")),
                ("🧠  Memory", "Browse stored memories", lambda: self._navigate("memory")),
                ("⚙  System", "System monitor", lambda: self._navigate("system")),
                ("🧩  Plugins", "Manage plugins", lambda: self._navigate("plugins")),
                ("🎨  Component Gallery", "Design-system tokens and components", lambda: self._navigate("gallery")),
                ("◈  Settings", "Open settings & themes", lambda: self._navigate("settings")),
                ("⬇  Export Chat", "Save conversation to markdown", self._on_chat_export_request),
                ("↺  Regenerate", "Re-run the last AI prompt", self._on_chat_regenerate),
                ("⟨  Toggle Sidebar", "Collapse or expand sidebar", self._sidebar.toggle_collapse),
                ("⏱  Command History", "Browse recent commands (Ctrl+H)", self._history_drawer.toggle),
                ("?  Shortcuts", "Show keyboard shortcut overlay", self._shortcut_overlay.show),
                (
                    "🤖  Supervised Agent Demo",
                    "Spawn a permission-gated agent run (visible in System view)",
                    lambda: self._on_command("agent: demo"),
                ),
            ]
        )
        self._command_palette.show(commands)

    def _workspace_os_palette_commands(self) -> list[tuple[str, str, Callable[[], None]]]:
        """Build launchable Workspace OS entity commands from AppState."""
        items: list[tuple[str, str, Callable[[], None]]] = []
        for entity in self._controller.snapshot().workspace_os.entities:
            meta = dict(entity.metadata)
            resource_type = meta.get("resource_type")
            value = meta.get("url") or meta.get("path") or meta.get("command") or ""
            chat_payload = {
                "entity_id": entity.entity_id,
                "entity_type": entity.entity_type,
                "title": entity.title or entity.entity_id,
            }
            if meta.get("description"):
                chat_payload["description"] = str(meta["description"])
            if meta.get("url"):
                chat_payload["url"] = str(meta["url"])
            elif meta.get("path"):
                chat_payload["path"] = str(meta["path"])
            elif meta.get("command"):
                chat_payload["path"] = str(meta["command"])
            chat_label = f"💬  Chat: {entity.title or entity.entity_id}"
            chat_desc = f"Open chat attached to {entity.entity_type}"
            items.append(
                (
                    chat_label,
                    chat_desc,
                    lambda p=chat_payload: self._on_open_chat_from_workspace(p),
                )
            )
            if not resource_type or not value:
                continue
            label = f"🚀  {entity.title}"
            desc = f"Workspace OS {entity.entity_type} ({resource_type})"
            payload = {
                "resource_id": entity.entity_id,
                "resource_type": resource_type,
                "value": value,
            }
            items.append(
                (label, desc, lambda p=payload: self._controller.publish_launch_resource(p))
            )
        return items

    def _maybe_show_shortcuts(self, event) -> None:
        focused = self.focus_get()
        if isinstance(focused, (ctk.CTkEntry, ctk.CTkTextbox)):
            return
        self._shortcut_overlay.show()

    def _on_settings_save(self, key: str, value: str) -> None:
        self._controller.request_settings_change(key, value)
        if key == "theme":
            theme_manager.apply(self, theme_name=value)
            self._toast.show(f'Theme "{value}" applied', kind="success")
        elif key == "window_alpha":
            try:
                theme_manager.apply(self, alpha=float(value))
            except ValueError:
                pass

    def _on_chat_export(self, history: list[dict]) -> None:
        if history:
            self._controller.publish_chat_export(list(history))
        else:
            self._toast.show("No chat history to export", kind="warning")

    def _on_chat_export_request(self) -> None:
        chat = self._chat_view()
        self._on_chat_export(list(chat._history) if chat else [])

    def _on_chat_export_result(self, event: Event) -> None:
        path = str(event.payload.get("path", ""))

        def _open_file(p: str = path) -> None:
            try:
                os.startfile(p)  # type: ignore[attr-defined]
            except Exception:
                pass

        self._ui_queue.enqueue(
            lambda: self._toast.show(
                f"Saved to {path}",
                kind="success",
                duration=6000,
                action=("Open", _open_file),
            )
        )

    def _on_chat_export_error(self, event: Event) -> None:
        message = str(event.payload.get("message", "Export failed"))
        self._ui_queue.enqueue(
            lambda: self._toast.show(f"Export failed: {message}", kind="error")
        )

    def _on_chat_regenerate(self) -> None:
        chat = self._chat_view()
        if chat and chat._history:
            entity = self._controller.active_chat_workspace_entity()
            for msg in reversed(chat._history):
                if msg.get("role") == "user":
                    self._on_command(msg.get("content", ""), workspace_entity=entity)
                    return

    def _on_memory_delete(self, memory_id: str | None, text: str = "") -> None:
        if memory_id:
            self._controller.publish_memory_delete(memory_id)

    def _on_memory_add(self, label: str, content: str) -> None:
        self._controller.publish_memory_remember(
            label,
            content,
            workspace_scope=self._controller.current_workspace_scope(),
        )

    def _on_command(self, text: str, *, workspace_entity: dict[str, str] | None = None) -> None:
        lower = text.strip().lower()
        if lower in ("?", "help"):
            self._show_capability_help()
            return

        if not text.startswith(".rating:"):
            self._history_drawer.push(text.strip())

        clipboard: str | None = None
        if wants_clipboard(text):
            clipboard = self._controller.read_clipboard()
            if not clipboard:
                message = empty_clipboard_message()

                def update() -> None:
                    self._navigate("chat")
                    chat = self._chat_view()
                    if chat:
                        chat.show_error(message)

                self._ui_queue.enqueue(update)
                return

        if workspace_entity is None:
            workspace_entity = self._controller.active_chat_workspace_entity()
        if workspace_entity is None:
            scope = self._controller.current_workspace_scope()
            selected_id = str(
                scope.get("workspace_entity_id") or scope.get("selected_entity_id") or ""
            ).strip()
            if selected_id:
                workspace_entity = {
                    "entity_id": selected_id,
                    "entity_type": str(
                        scope.get("workspace_entity_type")
                        or scope.get("selected_entity_type")
                        or "entity"
                    ),
                    "entity_title": str(
                        scope.get("workspace_entity_title")
                        or scope.get("selected_entity_title")
                        or ""
                    ),
                }
        self._controller.publish_command(text, clipboard=clipboard, workspace_entity=workspace_entity)

    def _show_capability_help(self) -> None:
        show_capability_help(self)

    def _apply_overlay_geometry(self, mode: str, x: int, y: int) -> None:
        if mode == "compact":
            self.attributes("-topmost", True)
            if x > 0 and y > 0:
                self.geometry(f"640x420+{x}+{y}")
            else:
                self.geometry("640x420")
            self.minsize(480, 320)
        else:
            self.attributes("-topmost", False)
            self.geometry(f"{T.WINDOW_WIDTH}x{T.WINDOW_HEIGHT}")
            self.minsize(900, 560)

    def _fade_in(self, step: int = 0) -> None:
        target = theme_manager.active_alpha()
        alpha = min(target, (step + 1) / T.FADE_STEPS * target)
        self.attributes("-alpha", alpha)
        if step + 1 < T.FADE_STEPS:
            delay = max(1, T.FADE_IN_MS // T.FADE_STEPS)
            self.after(delay, lambda: self._fade_in(step + 1))

    def _fade_out(self, on_done) -> None:
        start_alpha = theme_manager.active_alpha()

        def step(n: int) -> None:
            alpha = max(0.0, start_alpha - (n + 1) / T.FADE_STEPS * start_alpha)
            self.attributes("-alpha", alpha)
            if n + 1 < T.FADE_STEPS:
                delay = max(1, T.FADE_IN_MS // T.FADE_STEPS)
                self.after(delay, lambda: step(n + 1))
            else:
                on_done()

        step(0)

    def show(self) -> None:
        if self._visible:
            self.lift()
            self.focus_force()
            self._command_box.focus()
            return
        self._visible = True
        self.deiconify()
        self.lift()
        self.focus_force()
        self._command_box.focus()
        self._fade_in()

    def hide(self) -> None:
        if not self._visible:
            return
        self._visible = False

        def done() -> None:
            self.withdraw()
            self.attributes("-topmost", False)

        self._fade_out(done)

    def toggle(self) -> None:
        if self._visible:
            self.hide()
        else:
            self.show()

    def is_visible(self) -> bool:
        return self._visible

    def destroy(self) -> None:
        if self._current_view and self._current_view in self._views:
            prev = self._views[self._current_view]
            if hasattr(prev, "on_hide"):
                prev.on_hide()
        for unsub in self._bus_unsubs:
            try:
                unsub()
            except Exception:
                pass
        self._bus_unsubs.clear()
        self._controller.close()
        super().destroy()

    def tray_phase(self) -> str:
        return self._controller.snapshot().phase
