"""UI bridge — EventBus and AppState only (no ApplicationCore)."""

from __future__ import annotations

from collections.abc import Callable

try:
    import pyperclip
except Exception:  # pragma: no cover - optional clipboard dependency
    pyperclip = None

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import (
    AGENT_CANCEL_REQUEST,
    CHAT_EXPORT_REQUEST,
    CLIPBOARD_CONTENT,
    CLIPBOARD_REQUEST,
    ENTITY_CREATE_REQUEST,
    MEMORY_DELETE_REQUEST,
    MEMORY_REMEMBER,
    NOTE_SELECT,
    OVERLAY_ANCHOR,
    OVERLAY_HIDE,
    OVERLAY_SHOW,
    PERMISSION_CHECK_RESULT,
    PLUGIN_DISABLE_REQUEST,
    PLUGIN_ENABLE_REQUEST,
    UI_INSPECT_CLEAR,
    UI_INSPECT_NAVIGATE,
    UI_INSPECT_SELECT,
    SETTINGS_SET_REQUEST,
    UI_CHAT_CANCEL,
    UI_CHAT_NEW_SESSION,
    UI_COMMAND,
    UI_LAUNCH_RESOURCE,
    UI_NAVIGATE,
    UI_OPEN_CHAT,
    UI_ARTIFACT_ACTION,
    UI_PALETTE_CLOSE,
    UI_PALETTE_OPEN,
    UI_SELECT_WORKSPACE,
    EXECUTION_QUERY_REQUEST,
    UI_EXECUTION_TIMELINE_SCRUB,
    UI_WORKFLOW_NODE_SELECT,
    UI_WORKFLOW_NODE_MOVE,
    UI_AUTOMATION_RUN,
    UI_AUTOMATION_SCHEDULE_TOGGLE,
    UI_AUTOMATION_SELECT,
    UI_WORKFLOW_RUN,
    WORKFLOW_START,
    WORLD_MODEL_NODE_SELECTED,
)


class UIController:
    """
    Mediates UI intents → EventBus.
    UI reads AppState via snapshot + subscribe callbacks.
    """

    def __init__(
        self,
        bus: EventBus,
        state_store: AppStateStore,
        on_state: Callable[[], None],
    ) -> None:
        self._bus = bus
        self._state_store = state_store
        self._on_state = on_state
        self._unsub_state: Callable[[], None] | None = None
        self._unsub_state = self._state_store.subscribe(lambda _s: on_state())

    def close(self) -> None:
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None

    def snapshot(self):
        return self._state_store.snapshot

    def active_chat_workspace_entity(self) -> dict[str, str] | None:
        """Active workspace entity from AppState (chat attach), if any."""
        snap = self._state_store.snapshot
        entity_id = str(snap.chat_workspace_entity_id).strip()
        if not entity_id:
            return None
        entity: dict[str, str] = {
            "entity_id": entity_id,
            "entity_type": snap.chat_workspace_entity_type,
            "entity_title": snap.chat_workspace_entity_title,
        }
        if snap.chat_workspace_entity_description:
            entity["description"] = snap.chat_workspace_entity_description
        if snap.chat_workspace_entity_url:
            entity["url"] = snap.chat_workspace_entity_url
        if snap.chat_workspace_entity_path:
            entity["path"] = snap.chat_workspace_entity_path
        return entity

    def current_workspace_scope(self) -> dict[str, str]:
        """Workspace scope derived from AppState for UI-originated intents."""
        snap = self._state_store.snapshot
        workspace_entity = getattr(snap, "workspace_entity", None)
        scope: dict[str, str] = {}
        active_ws = str(
            getattr(workspace_entity, "active_workspace_id", snap.active_workspace_id)
        ).strip()
        if active_ws:
            scope["workspace_id"] = active_ws
            title = str(
                getattr(workspace_entity, "active_workspace_title", snap.active_workspace_title)
            ).strip()
            if title:
                scope["active_workspace_title"] = title
        entity = self.active_chat_workspace_entity()
        if entity is None:
            selected_id = str(
                getattr(workspace_entity, "selected_entity_id", snap.selected_entity_id)
            ).strip()
            if selected_id:
                scope["workspace_entity_id"] = selected_id
                selected_type = str(
                    getattr(workspace_entity, "selected_entity_type", snap.selected_entity_type)
                ).strip()
                selected_title = str(
                    getattr(workspace_entity, "selected_entity_title", snap.selected_entity_title)
                ).strip()
                if selected_type:
                    scope["workspace_entity_type"] = selected_type
                if selected_title:
                    scope["workspace_entity_title"] = selected_title
                scope["selected_entity_id"] = selected_id
                if selected_type:
                    scope["selected_entity_type"] = selected_type
                if selected_title:
                    scope["selected_entity_title"] = selected_title
            return scope
        scope["workspace_entity_id"] = entity["entity_id"]
        scope["workspace_entity_type"] = entity.get("entity_type", "")
        scope["workspace_entity_title"] = entity.get("entity_title", "")
        if entity.get("entity_type") == "workspace":
            scope["workspace_id"] = entity["entity_id"]
        for src, dst in (
            ("description", "workspace_entity_description"),
            ("url", "workspace_entity_url"),
            ("path", "workspace_entity_path"),
        ):
            value = str(entity.get(src, "")).strip()
            if value:
                scope[dst] = value
        return scope

    def publish_command(
        self,
        text: str,
        *,
        clipboard: str | None = None,
        workspace_entity: dict[str, str] | None = None,
    ) -> None:
        payload: dict[str, str] = {"text": text}
        if clipboard:
            payload["clipboard"] = clipboard
        if workspace_entity:
            entity_id = str(workspace_entity.get("entity_id", "")).strip()
            if entity_id:
                payload["workspace_entity_id"] = entity_id
                payload["workspace_entity_type"] = str(
                    workspace_entity.get("entity_type", "")
                )
                payload["workspace_entity_title"] = str(
                    workspace_entity.get("entity_title", "")
                )
                description = str(workspace_entity.get("description", "")).strip()
                url = str(workspace_entity.get("url", "")).strip()
                path = str(workspace_entity.get("path", "")).strip()
                if description:
                    payload["workspace_entity_description"] = description
                if url:
                    payload["workspace_entity_url"] = url
                if path:
                    payload["workspace_entity_path"] = path
                if str(workspace_entity.get("entity_type", "")) == "workspace":
                    payload["workspace_id"] = entity_id
        scope = self.current_workspace_scope()
        for key, value in scope.items():
            if key not in payload and value:
                payload[key] = value
        self._bus.publish(
            UI_COMMAND,
            payload,
            source="ui",
        )

    def publish_navigate(self, view_id: str) -> None:
        self._bus.publish(
            UI_NAVIGATE,
            {"view": view_id},
            source="ui",
        )

    def publish_inspect_select(
        self,
        kind: str,
        ref_id: str,
        *,
        label: str = "",
        payload: dict[str, str] | None = None,
    ) -> None:
        self._bus.publish(
            UI_INSPECT_SELECT,
            {
                "kind": kind,
                "ref_id": ref_id,
                "label": label,
                "payload": {str(k): str(v) for k, v in (payload or {}).items()},
            },
            source="ui",
        )

    def publish_inspect_clear(self) -> None:
        self._bus.publish(UI_INSPECT_CLEAR, {}, source="ui")

    def publish_inspect_navigate(
        self,
        kind: str,
        ref_id: str,
        *,
        label: str = "",
    ) -> None:
        payload: dict[str, object] = {"kind": kind, "ref_id": ref_id}
        if label:
            payload["label"] = label
        self._bus.publish(
            UI_INSPECT_NAVIGATE,
            payload,
            source="ui",
        )

    def publish_artifact_action(self, artifact_id: str, action: str) -> None:
        self._bus.publish(
            UI_ARTIFACT_ACTION,
            {"artifact_id": artifact_id, "action": action},
            source="ui",
        )

    def publish_execution_query(self, request_id: str) -> None:
        self._bus.publish(
            EXECUTION_QUERY_REQUEST,
            {"request_id": request_id},
            source="ui",
        )

    def publish_execution_timeline_scrub(self, request_id: str, index: int) -> None:
        self._bus.publish(
            UI_EXECUTION_TIMELINE_SCRUB,
            {"request_id": request_id, "index": index},
            source="ui",
        )

    def publish_workflow_node_select(
        self,
        node_id: str,
        *,
        workflow_id: str = "",
        label: str = "",
        kind: str = "step",
        state: str = "",
    ) -> None:
        self._bus.publish(
            UI_WORKFLOW_NODE_SELECT,
            {
                "node_id": node_id,
                "workflow_id": workflow_id,
                "label": label,
                "kind": kind,
                "state": state,
            },
            source="ui",
        )

    def publish_workflow_node_move(
        self,
        node_id: str,
        x: float,
        y: float,
        *,
        workflow_id: str = "",
    ) -> None:
        self._bus.publish(
            UI_WORKFLOW_NODE_MOVE,
            {
                "node_id": node_id,
                "x": x,
                "y": y,
                "workflow_id": workflow_id,
            },
            source="ui",
        )

    def publish_workflow_run(
        self,
        workflow_id: str,
        steps: list[dict[str, object]],
        *,
        run_id: str = "",
    ) -> None:
        payload: dict[str, object] = {
            "workflow_id": workflow_id,
            "steps": steps,
        }
        if run_id:
            payload["run_id"] = run_id
        self._bus.publish(
            UI_WORKFLOW_RUN,
            {"workflow_id": workflow_id, "steps": steps},
            source="ui",
        )
        self._bus.publish(WORKFLOW_START, payload, source="ui")

    def publish_automation_run(self, workflow_id: str) -> None:
        from ai_command_center.core.projectors.automation_workspace_projector import (
            AutomationWorkspaceProjector,
        )

        steps = AutomationWorkspaceProjector.steps_for_workflow(workflow_id)
        self._bus.publish(
            UI_AUTOMATION_RUN,
            {"workflow_id": workflow_id},
            source="ui",
        )
        self.publish_workflow_run(workflow_id, steps)

    def publish_automation_select(self, run_id: str, *, workflow_id: str = "", label: str = "") -> None:
        self._bus.publish(
            UI_AUTOMATION_SELECT,
            {"run_id": run_id, "workflow_id": workflow_id, "label": label},
            source="ui",
        )

    def publish_automation_schedule_toggle(self, schedule_id: str) -> None:
        self._bus.publish(
            UI_AUTOMATION_SCHEDULE_TOGGLE,
            {"schedule_id": schedule_id},
            source="ui",
        )

    def publish_palette_open(self) -> None:
        self._bus.publish(UI_PALETTE_OPEN, {}, source="ui")
        self._bus.publish(OVERLAY_SHOW, {"mode": "palette", "x": 0, "y": 0}, source="ui")

    def publish_palette_close(self) -> None:
        self._bus.publish(UI_PALETTE_CLOSE, {}, source="ui")
        self._bus.publish(OVERLAY_HIDE, {}, source="ui")

    def publish_overlay_show(self, *, mode: str = "compact", x: int = 0, y: int = 0) -> None:
        self._bus.publish(
            OVERLAY_SHOW,
            {"mode": mode, "x": x, "y": y},
            source="ui",
        )

    def publish_overlay_anchor(self, x: int, y: int) -> None:
        self._bus.publish(OVERLAY_ANCHOR, {"x": x, "y": y}, source="ui")

    def request_settings_change(self, key: str, value: str) -> None:
        self._bus.publish(
            SETTINGS_SET_REQUEST,
            {"key": key, "value": value},
            source="ui",
        )

    def publish_chat_cancel(self, request_id: str) -> None:
        self._bus.publish(
            UI_CHAT_CANCEL,
            {"request_id": request_id},
            source="ui",
        )

    def publish_memory_remember(
        self,
        label: str,
        content: str,
        *,
        workspace_scope: dict[str, str] | None = None,
    ) -> None:
        payload = {"label": label, "content": content}
        if workspace_scope:
            payload.update(workspace_scope)
        self._bus.publish(
            MEMORY_REMEMBER,
            payload,
            source="ui",
        )

    def publish_launch_resource(self, payload: dict[str, object]) -> None:
        self._bus.publish(UI_LAUNCH_RESOURCE, payload, source="ui")

    def publish_select_workspace(self, workspace_id: str) -> None:
        """Activate a workspace as the runtime scope anchor."""
        self._bus.publish(
            UI_SELECT_WORKSPACE,
            {"workspace_id": workspace_id},
            source="ui",
        )

    def publish_open_chat(
        self,
        entity_id: str,
        entity_type: str,
        title: str,
        *,
        description: str = "",
        url: str = "",
        path: str = "",
        workspace_id: str = "",
    ) -> None:
        payload: dict[str, str] = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "title": title,
        }
        if description:
            payload["description"] = description
        if url:
            payload["url"] = url
        if path:
            payload["path"] = path
        ws_id = str(workspace_id).strip()
        if not ws_id and entity_type not in ("", "workspace"):
            ws_id = str(self._state_store.snapshot.active_workspace_id).strip()
        if ws_id:
            payload["workspace_id"] = ws_id
        self._bus.publish(UI_OPEN_CHAT, payload, source="ui")

    def publish_clear_chat_entity(self) -> None:
        """Detach workspace entity context (generic chat navigation)."""
        self._bus.publish(UI_OPEN_CHAT, {"entity_id": ""}, source="ui")

    def publish_chat_new_session(self) -> None:
        """Start a fresh generic chat session and clear entity attach."""
        self._bus.publish(UI_CHAT_NEW_SESSION, {}, source="ui")

    def publish_note_select(self, path: str) -> None:
        self._bus.publish(
            NOTE_SELECT,
            {"path": path},
            source="ui",
        )

    def publish_plugin_toggle(self, plugin_id: str, enabled: bool) -> None:
        topic = PLUGIN_ENABLE_REQUEST if enabled else PLUGIN_DISABLE_REQUEST
        self._bus.publish(topic, {"id": plugin_id}, source="ui")

    def publish_memory_delete(self, memory_id: str) -> None:
        self._bus.publish(
            MEMORY_DELETE_REQUEST,
            {"id": memory_id},
            source="ui",
        )

    def publish_chat_export(self, history: list[dict]) -> None:
        self._bus.publish(
            CHAT_EXPORT_REQUEST,
            {"history": list(history)},
            source="ui",
        )

    def publish_permission_result(
        self,
        *,
        check_id: str,
        granted: bool,
        permissions: list[str] | tuple[str, ...],
        actor_type: str = "agent",
        actor_id: str = "",
    ) -> None:
        """Publish user approval/denial for interactive permission checks."""
        self._bus.publish(
            PERMISSION_CHECK_RESULT,
            {
                "check_id": check_id,
                "granted": granted,
                "permissions": list(permissions),
                "actor_type": actor_type,
                "actor_id": actor_id,
            },
            source="ui",
        )

    def read_clipboard(self) -> str | None:
        if pyperclip is None:
            return None
        try:
            text = pyperclip.paste()
        except Exception:
            return None
        if not text or not str(text).strip():
            return None
        return str(text)

    def publish_clipboard_request(self) -> None:
        self._bus.publish(CLIPBOARD_REQUEST, {}, source="ui")
        try:
            text = self.read_clipboard()
        except Exception:
            text = None
        if text:
            self._bus.publish(CLIPBOARD_CONTENT, {"text": text}, source="ui")

    def publish_world_model_node_selected(self, node_id: str) -> None:
        """Publish world-model node selection intent."""
        self._bus.publish(
            WORLD_MODEL_NODE_SELECTED,
            {"node_id": str(node_id)},
            source="ui",
        )

    def publish_entity_create_request(
        self,
        *,
        entity_type: str = "note",
        title: str = "New Entity",
        description: str = "",
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Publish entity creation intent (never WORLD_MODEL_MUTATION_APPLIED)."""
        self._bus.publish(
            ENTITY_CREATE_REQUEST,
            {
                "entity_type": str(entity_type),
                "title": str(title),
                "description": str(description),
                "metadata": dict(metadata or {}),
            },
            source="ui",
        )

    def publish_agent_cancel_request(
        self,
        agent_id: str,
        *,
        reason: str = "cancelled",
    ) -> None:
        """Publish contextual agent cancel intent (AgentRuntimeService subscriber)."""
        aid = str(agent_id).strip()
        if not aid:
            return
        self._bus.publish(
            AGENT_CANCEL_REQUEST,
            {"agent_id": aid, "reason": str(reason or "cancelled")},
            source="ui",
        )
