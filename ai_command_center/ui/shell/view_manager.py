"""View registration, lazy creation, and navigation."""

from __future__ import annotations

from collections.abc import Callable

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.views.chat_view import ChatView
from ai_command_center.ui.views.component_gallery_view import ComponentGalleryView
from ai_command_center.ui.views.executions_view import ExecutionsView
from ai_command_center.ui.views.home_view import HomeView
from ai_command_center.ui.views.memory_view import MemoryView
from ai_command_center.ui.views.notes_view import NotesView
from ai_command_center.ui.views.placeholder import PlaceholderView
from ai_command_center.ui.views.plugins_view import PluginsView
from ai_command_center.ui.views.providers_view import ProvidersView
from ai_command_center.ui.views.capabilities_view import CapabilitiesView
from ai_command_center.ui.views.artifacts_view import ArtifactsView
from ai_command_center.ui.views.settings_view import SettingsView
from ai_command_center.ui.views.system_view import SystemView
from ai_command_center.ui.views.workspace_view import WorkspaceView
from ai_command_center.ui.workspace_os_controller import WorkspaceOsUIController

ViewFactory = Callable[[], object]

VIEW_IDS: tuple[str, ...] = (
    "workspace",
    "home",
    "chat",
    "executions",
    "providers",
    "capabilities",
    "artifacts",
    "notes",
    "memory",
    "system",
    "plugins",
    "settings",
    "gallery",
)


class ViewManagerMixin:
    """Registers view factories and manages show/hide lifecycle."""

    def _register_views(self) -> None:
        """Register all view factories. Add new views here only."""
        ws_controller = WorkspaceOsUIController(self._bus)
        self._view_registry["workspace"] = lambda: WorkspaceView(
            self._content,
            on_launch=self._controller.publish_launch_resource,
            on_open_chat=self._on_open_chat_from_workspace,
            on_command=self._on_command,
            ws_controller=ws_controller,
        )
        self._view_registry["home"] = lambda: HomeView(
            self._content,
            on_command=self._on_command,
        )
        self._view_registry["chat"] = lambda: ChatView(
            self._content,
            on_cancel=self._controller.publish_chat_cancel,
            on_export=self._on_chat_export,
            on_regenerate=self._on_chat_regenerate,
            on_send=self._on_chat_send,
            on_new_session=self._on_chat_new_session,
            on_inspect_select=self._on_chat_inspect_select,
            on_inspect_navigate=self._on_chat_inspect_navigate,
            on_artifact_action=self._controller.publish_artifact_action,
        )
        self._view_registry["notes"] = lambda: NotesView(
            self._content,
            on_select=self._on_note_select,
            on_search=lambda q: self._on_command(f"note: {q}"),
            on_create=self._on_note_create,
        )
        self._view_registry["memory"] = lambda: MemoryView(
            self._content,
            on_delete=self._on_memory_delete,
            on_add=self._on_memory_add,
        )
        self._view_registry["system"] = lambda: SystemView(self._content)
        self._view_registry["settings"] = lambda: SettingsView(
            self._content,
            on_save=self._on_settings_save,
        )
        self._view_registry["plugins"] = lambda: PluginsView(
            self._content,
            on_toggle=self._controller.publish_plugin_toggle,
        )
        self._view_registry["executions"] = lambda: ExecutionsView(
            self._content,
            on_select=self._on_execution_select,
            on_scrub=self._on_execution_timeline_scrub,
        )
        self._view_registry["providers"] = lambda: ProvidersView(self._content)
        self._view_registry["capabilities"] = lambda: CapabilitiesView(self._content)
        self._view_registry["artifacts"] = lambda: ArtifactsView(
            self._content,
            on_artifact_action=self._controller.publish_artifact_action,
        )
        self._view_registry["gallery"] = lambda: ComponentGalleryView(self._content)

    def _ensure_view(self, view_id: str) -> object:
        if view_id not in self._views:
            factory = self._view_registry.get(view_id)
            if factory is not None:
                self._views[view_id] = factory()
            else:
                self._views[view_id] = PlaceholderView(self._content, view_id)
        return self._views[view_id]

    def _home_view(self) -> HomeView | None:
        v = self._views.get("home")
        return v if isinstance(v, HomeView) else None

    def _system_view(self) -> SystemView | None:
        v = self._views.get("system")
        return v if isinstance(v, SystemView) else None

    def _notes_view(self) -> NotesView | None:
        v = self._views.get("notes")
        return v if isinstance(v, NotesView) else None

    def _chat_view(self) -> ChatView | None:
        v = self._views.get("chat")
        return v if isinstance(v, ChatView) else None

    def _memory_view(self) -> MemoryView | None:
        v = self._views.get("memory")
        return v if isinstance(v, MemoryView) else None

    def _plugins_view(self) -> PluginsView | None:
        v = self._views.get("plugins")
        return v if isinstance(v, PluginsView) else None

    def _workspace_view(self) -> WorkspaceView | None:
        v = self._views.get("workspace")
        return v if isinstance(v, WorkspaceView) else None

    def _workspace_os_routing_enabled(self) -> bool:
        return self._default_view == "workspace"

    def _policy_resolve_view(self, view_id: str) -> str:
        """Workspace-centric routing: chat consumes active workspace scope."""
        if not self._workspace_os_routing_enabled() or view_id != "chat":
            return view_id
        snap = self._controller.snapshot()
        if str(snap.active_workspace_id).strip():
            return "chat"
        return "workspace"

    def _show_view(self, view_id: str) -> None:
        if view_id not in VIEW_IDS:
            view_id = "home"
        prev_id = self._current_view
        if prev_id and prev_id in self._views:
            prev = self._views[prev_id]
            if hasattr(prev, "on_hide"):
                prev.on_hide()
        self._current_view = view_id
        for view in self._views.values():
            view.pack_forget()
        view = self._ensure_view(view_id)
        view.pack(fill="both", expand=True)
        if hasattr(view, "on_show"):
            view.on_show()
        self._sidebar.set_active(view_id)
        if view_id == "settings":
            settings_view = self._views.get("settings")
            if isinstance(settings_view, SettingsView):
                settings_view.load_from_snapshot(self._controller.snapshot().settings)
        if view_id == "chat":
            chat = self._chat_view()
            if chat:
                chat.focus_input()

    def _on_sidebar_navigate(self, view_id: str) -> None:
        self._navigate(view_id)

    def _navigate(self, view_id: str, *, clear_chat_entity: bool = False) -> None:
        view_id = self._policy_resolve_view(view_id)
        if view_id == "chat" and clear_chat_entity:
            self._controller.publish_clear_chat_entity()
        self._show_view(view_id)
        self._controller.publish_navigate(view_id)

    def _on_note_select(self, path: str, title: str) -> None:
        self._controller.publish_note_select(path)

    def _on_note_create(self, title: str, content: str) -> None:
        self._on_command(f"new note: {title} | {content}")

    def _on_open_chat_from_workspace(self, payload: dict) -> None:
        workspace_id = str(payload.get("workspace_id", "")).strip()
        entity_type = str(payload.get("entity_type", "")).strip()
        if workspace_id and entity_type in ("card", "resource", "note"):
            snap = self._controller.snapshot()
            if str(snap.active_workspace_id).strip() != workspace_id:
                self._controller.publish_select_workspace(workspace_id)
        self._controller.publish_open_chat(
            str(payload.get("entity_id", "")),
            entity_type,
            str(payload.get("title", "")),
            description=str(payload.get("description", "")),
            url=str(payload.get("url", "")),
            path=str(payload.get("path", "")),
            workspace_id=workspace_id,
        )
        self._navigate("chat")

    def _on_chat_new_session(self) -> None:
        self._controller.publish_chat_new_session()
        chat = self._chat_view()
        if chat:
            chat.reset_local_session()

    def _on_chat_send(self, text: str) -> None:
        self._on_command(text, workspace_entity=self._controller.active_chat_workspace_entity())

    def _on_chat_inspect_select(self, ref: InspectableRef) -> None:
        self._controller.publish_inspect_select(
            ref.kind,
            ref.ref_id,
            label=ref.label,
            payload=dict(ref.payload),
        )

    def _on_chat_inspect_navigate(self, ref: InspectableRef) -> None:
        self._controller.publish_inspect_navigate(ref.kind, ref.ref_id, label=ref.label)

    def _focus_inspect_navigate_target(self, ref: InspectableRef) -> None:
        """Best-effort focus in the destination workspace after inspect navigate."""
        if ref.kind == "artifact" and ref.ref_id:
            artifacts = self._artifacts_view()
            if artifacts is not None:
                artifacts._viewer.show(
                    ref.ref_id,
                    kind="text",
                    label=ref.label or ref.ref_id,
                )
        elif ref.kind == "message":
            chat = self._chat_view()
            if chat is not None:
                chat.focus_input()

    def _on_execution_select(self, request_id: str) -> None:
        """Open execution detail and request timeline projection."""
        self._navigate("executions")
        self._controller.publish_execution_query(request_id)

    def _on_execution_timeline_scrub(self, request_id: str, index: int) -> None:
        self._controller.publish_execution_timeline_scrub(request_id, index)

    def _executions_view(self) -> "ExecutionsView | None":
        v = self._views.get("executions")
        return v if isinstance(v, ExecutionsView) else None

    def _providers_view(self) -> ProvidersView | None:
        v = self._views.get("providers")
        return v if isinstance(v, ProvidersView) else None

    def _capabilities_view(self) -> CapabilitiesView | None:
        v = self._views.get("capabilities")
        return v if isinstance(v, CapabilitiesView) else None

    def _artifacts_view(self) -> ArtifactsView | None:
        v = self._views.get("artifacts")
        return v if isinstance(v, ArtifactsView) else None
