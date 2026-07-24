"""View registration, lazy creation, and navigation."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.views.chat.chat_view import ChatView
from ai_command_center.ui.views.agents_view import AgentsView
from ai_command_center.ui.views.approvals_view import ApprovalsView
from ai_command_center.ui.views.brain_view import BrainView
from ai_command_center.ui.views.command_center_view import CommandCenterView
from ai_command_center.ui.views.goal_view import GoalView
from ai_command_center.ui.views.executions_view import ExecutionsView
from ai_command_center.ui.views.evidence_view import EvidenceView
from ai_command_center.ui.views.operations_view import OperationsView
from ai_command_center.ui.views.memory_view import MemoryView
from ai_command_center.ui.views.notes_view import NotesView
from ai_command_center.ui.views.plugins_view import PluginsView
from ai_command_center.ui.views.providers_view import ProvidersView
from ai_command_center.ui.views.capabilities_view import CapabilitiesView
from ai_command_center.ui.views.artifacts_view import ArtifactsView
from ai_command_center.ui.views.execution_timeline_view import ExecutionTimelineView
from ai_command_center.ui.views.settings_view import SettingsView
from ai_command_center.ui.views.system_view import SystemView
from ai_command_center.ui.views.automation_workspace_view import AutomationWorkspaceView
from ai_command_center.ui.views.dependency_inspector_view import DependencyInspectorView
from ai_command_center.ui.views.relationship_view import RelationshipView
from ai_command_center.ui.views.workflow_graph_view import WorkflowGraphView
from ai_command_center.ui.views.world_explorer_view import WorldExplorerView
from ai_command_center.ui.views.graph_workspace_view import GraphWorkspaceView
from ai_command_center.ui.views.insights_view import InsightsView
from ai_command_center.ui.views.workspace_view import WorkspaceView
from ai_command_center.ui.workspace_os_controller import WorkspaceOsUIController
from ai_command_center.core.state.world_model_state import WorldModelState

ViewFactory = Callable[[], object]

VIEW_IDS: tuple[str, ...] = (
    "command_center",
    "workspace",
    "brain",
    "chat",
    "executions",
    "evidence",
    "operations",
    "goals",
    "agents",
    "approvals",
    "timeline",
    "workflow",
    "automation",
    "world_explorer",
    "graph_workspace",
    "insights",
    "relationships",
    "dependencies",
    "providers",
    "capabilities",
    "artifacts",
    "notes",
    "memory",
    "system",
    "plugins",
    "settings",
)


class ViewManagerMixin:
    """Registers view factories and manages show/hide lifecycle."""

    def _register_views(self) -> None:
        """Register all view factories. Add new views here only."""
        ws_controller = WorkspaceOsUIController(self._bus)
        self._world_model_state = WorldModelState(self._bus)
        self._view_registry["workspace"] = lambda: WorkspaceView(
            self._content,
            on_launch=self._controller.publish_launch_resource,
            on_open_chat=self._on_open_chat_from_workspace,
            on_command=self._on_command,
            ws_controller=ws_controller,
        )
        self._view_registry["command_center"] = lambda: CommandCenterView(
            self._content,
            on_command=self._on_command,
            on_navigate=self._navigate,
        )
        self._view_registry["brain"] = lambda: BrainView(
            self._content,
            on_select_goal=self._on_brain_goal_select,
            on_inspect_select=self._on_chat_inspect_select,
            on_navigate=self._navigate,
        )
        self._view_registry["goals"] = lambda: GoalView(
            self._content,
            on_new_goal=self._on_goal_new,
            on_select=self._on_goal_select,
            on_select_task=self._on_goal_task_select,
            on_inspect_select=self._on_chat_inspect_select,
            on_command=self._on_command,
            on_navigate=self._navigate,
        )
        self._view_registry["agents"] = lambda: AgentsView(
            self._content,
            on_select=self._on_agent_select,
            on_cancel=self._on_agent_cancel,
            on_inspect_select=self._on_chat_inspect_select,
            on_command=self._on_command,
            on_navigate=self._navigate,
        )
        self._view_registry["approvals"] = lambda: ApprovalsView(
            self._content,
            on_decide=self._on_approval_decide,
            on_select=self._on_approval_select,
            on_command=self._on_command,
            on_navigate=self._navigate,
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
            on_select=self._on_memory_select,
            on_inspect_select=self._on_chat_inspect_select,
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
            on_navigate=self._navigate,
        )
        self._view_registry["evidence"] = lambda: EvidenceView(
            self._content,
            on_select=self._on_evidence_select,
            on_inspect_select=self._on_chat_inspect_select,
            on_navigate=self._navigate,
        )
        self._view_registry["operations"] = lambda: OperationsView(
            self._content,
            on_select_operation=self._on_operation_select,
            on_scrub=self._on_operation_scrub,
            on_inspect_select=self._on_chat_inspect_select,
            on_navigate=self._navigate,
        )
        self._view_registry["timeline"] = lambda: ExecutionTimelineView(
            self._content,
            on_inspect_select=self._on_chat_inspect_select,
            on_inspect_navigate=self._on_chat_inspect_navigate,
        )
        self._view_registry["workflow"] = lambda: WorkflowGraphView(
            self._content,
            on_run=self._on_workflow_run,
            on_node_select=self._on_workflow_node_select,
            on_node_move=self._on_workflow_node_move,
            on_compare=self._on_workflow_compare,
            on_scrub=self._on_workflow_timeline_scrub,
        )
        self._view_registry["automation"] = lambda: AutomationWorkspaceView(
            self._content,
            on_run=self._on_automation_run,
            on_select_failure=self._on_automation_select_failure,
            on_select_run=self._on_automation_select_run,
            on_schedule_toggle=self._on_automation_schedule_toggle,
            on_template_run=self._on_automation_run,
            on_scrub=self._on_automation_timeline_scrub,
        )
        self._view_registry["providers"] = lambda: ProvidersView(self._content)
        self._view_registry["capabilities"] = lambda: CapabilitiesView(self._content)
        self._view_registry["artifacts"] = lambda: ArtifactsView(
            self._content,
            on_artifact_action=self._controller.publish_artifact_action,
        )
        self._view_registry["world_explorer"] = lambda: WorldExplorerView(
            self._content,
            on_select=self._on_world_node_select,
            on_filter_change=self._on_world_filter_change,
            on_inspect_select=self._on_chat_inspect_select,
            on_create_entity=self._on_world_model_create_entity,
            on_navigate=self._navigate,
        )
        self._view_registry["graph_workspace"] = lambda: GraphWorkspaceView(
            self._content,
            on_select=self._on_graph_select,
            on_filter_change=self._on_graph_filter_change,
            on_activate=self._on_graph_activate,
            on_inspect_select=self._on_chat_inspect_select,
            on_navigate=self._navigate,
        )
        self._view_registry["insights"] = lambda: InsightsView(
            self._content,
            on_refresh=self._on_insights_refresh,
            on_navigate=self._navigate,
        )
        self._view_registry["relationships"] = lambda: RelationshipView(
            self._content,
            bus=self._bus,
            state=self._world_model_state,
        )
        self._view_registry["dependencies"] = lambda: DependencyInspectorView(
            self._content,
            bus=self._bus,
            state=self._world_model_state,
        )

    def _ensure_view(self, view_id: str) -> object:
        if view_id not in self._views:
            factory = self._view_registry.get(view_id)
            if factory is not None:
                view = factory()
                self._views[view_id] = view
                if view_id == "timeline" and hasattr(view, "apply_state"):
                    view.apply_state(list(self._controller.snapshot().execution_timeline.events))
            else:
                self._views[view_id] = ctk.CTkLabel(
                    self._content,
                    text=f"View '{view_id}' is not registered",
                    font=("Segoe UI", 14),
                    text_color="red",
                )
        return self._views[view_id]

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

    def _command_center_view(self) -> CommandCenterView | None:
        v = self._views.get("command_center")
        return v if isinstance(v, CommandCenterView) else None

    def _brain_view(self) -> BrainView | None:
        v = self._views.get("brain")
        return v if isinstance(v, BrainView) else None

    def _world_explorer_view(self) -> WorldExplorerView | None:
        v = self._views.get("world_explorer")
        return v if isinstance(v, WorldExplorerView) else None

    def _graph_workspace_view(self) -> GraphWorkspaceView | None:
        v = self._views.get("graph_workspace")
        return v if isinstance(v, GraphWorkspaceView) else None

    def _insights_view(self) -> InsightsView | None:
        v = self._views.get("insights")
        return v if isinstance(v, InsightsView) else None

    def _evidence_view(self) -> EvidenceView | None:
        v = self._views.get("evidence")
        return v if isinstance(v, EvidenceView) else None

    def _operations_view(self) -> OperationsView | None:
        v = self._views.get("operations")
        return v if isinstance(v, OperationsView) else None

    def _on_world_model_create_entity(self) -> None:
        """Hero New Entity → ENTITY_CREATE_REQUEST via UIController."""
        self._controller.publish_entity_create_request(
            entity_type="note",
            title="New Entity",
        )

    def _on_world_node_select(self, node_id: str) -> None:
        """World Explorer node click → UI_WORLD_SELECT + domain + inspect."""
        nid = str(node_id).strip()
        if not nid:
            return
        self._controller.publish_world_select(nid)
        self._controller.publish_world_model_node_selected(nid)
        self._controller.publish_inspect_select(
            "world_node",
            nid,
            label=nid,
            payload={"node_id": nid},
        )

    def _on_world_filter_change(self, state: object) -> None:
        """Shared filter bar → UI_WORLD_FILTER intent (projection stays local)."""
        search = str(getattr(state, "search", "") or "")
        type_filter = str(getattr(state, "type_filter", "all") or "all")
        status_filter = str(getattr(state, "status_filter", "all") or "all")
        sort_key = str(getattr(state, "sort_key", "name") or "name")
        self._controller.publish_world_filter(
            search=search,
            type_filter=type_filter,
            status_filter=status_filter,
            sort_key=sort_key,
        )

    def _on_graph_select(self, node_id: str) -> None:
        """Graph Workspace node click → UI_GRAPH_SELECT + domain selection."""
        nid = str(node_id).strip()
        if not nid:
            return
        self._controller.publish_graph_select(nid)
        self._controller.publish_world_model_node_selected(nid)

    def _on_graph_filter_change(self, state: object) -> None:
        """Graph Workspace filter bar → UI_GRAPH_FILTER (projection stays local)."""
        search = str(getattr(state, "search", "") or "")
        type_filter = str(getattr(state, "type_filter", "all") or "all")
        status_filter = str(getattr(state, "status_filter", "all") or "all")
        sort_key = str(getattr(state, "sort_key", "name") or "name")
        self._controller.publish_graph_filter(
            search=search,
            type_filter=type_filter,
            status_filter=status_filter,
            sort_key=sort_key,
        )

    def _on_graph_activate(self, node_id: str) -> None:
        """Double-click → UI_GRAPH_NAVIGATE + open World Explorer."""
        nid = str(node_id).strip()
        if not nid:
            return
        self._controller.publish_graph_navigate(nid, view="world_explorer")
        self._navigate("world_explorer")

    def _on_insights_refresh(self) -> None:
        """Insights placeholder Refresh → UI_INSIGHTS_REFRESH."""
        self._controller.publish_insights_refresh()

    def _workspace_os_routing_enabled(self) -> bool:
        return getattr(self, "_workspace_os_enabled", self._default_view == "workspace")

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
            view_id = "command_center"
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

        if hasattr(self, "_queue_state_refresh"):
            self._queue_state_refresh()

    def _on_sidebar_navigate(self, view_id: str) -> None:
        self._navigate(view_id)

    def _navigate(self, view_id: str, *, clear_chat_entity: bool = False) -> None:
        """Show a view and publish UI_NAVIGATE once — never re-enter.

        Re-entrancy (bus handler → _navigate → publish → handler) previously
        froze the shell after a couple of sidebar clicks. Same-view calls are
        no-ops so chatter cannot storm the bus.
        """
        if getattr(self, "_navigate_reentrant", False):
            return
        view_id = self._policy_resolve_view(view_id)
        if (
            view_id == getattr(self, "_current_view", None)
            and view_id in getattr(self, "_views", {})
            and not clear_chat_entity
        ):
            return
        self._navigate_reentrant = True
        try:
            if view_id == "chat" and clear_chat_entity:
                self._controller.publish_clear_chat_entity()
            self._show_view(view_id)
            # Publish after the current Tk turn so SYNC_CRITICAL bus handlers
            # never nest inside pack/on_show/_apply_state on the click stack.
            target = view_id

            def _publish_navigate() -> None:
                self._controller.publish_navigate(target)

            after = getattr(self, "after", None)
            if callable(after):
                after(0, _publish_navigate)
            else:
                _publish_navigate()
        finally:
            self._navigate_reentrant = False

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

    def _on_agent_select(self, agent_id: str) -> None:
        """Agent Operations select → UI_AGENT_SELECT + enriched inspect."""
        aid = str(agent_id).strip()
        if not aid:
            return
        self._controller.publish_agent_select(aid)
        snap = self._controller.snapshot()
        run = snap.agent_pipeline.run_by_id(aid)
        payload: dict[str, object] = {"agent_id": aid}
        if run is not None:
            payload.update(
                {
                    "name": run.spawn_role or aid,
                    "role": run.spawn_role,
                    "status": run.state,
                    "task": run.task,
                    "error": run.error,
                    "steps": run.steps,
                    "pipeline_id": snap.agent_pipeline.pipeline_id,
                    "pipeline_stage": snap.agent_pipeline.pipeline_stage,
                }
            )
        self._controller.publish_inspect_select(
            "agent",
            aid,
            label=str(payload.get("name") or aid),
            payload=payload,
        )

    def _on_approval_select(self, check_id: str) -> None:
        """Focus a pending approval check via existing inspect selection flow."""
        cid = str(check_id).strip()
        if not cid:
            return
        self._controller.publish_inspect_select(
            "approval",
            cid,
            label=cid,
            payload={"check_id": cid},
        )

    def _on_goal_select(self, goal_id: str) -> None:
        """Goal Workspace / Brain focus → UI_GOAL_SELECT + inspect."""
        gid = str(goal_id).strip()
        if not gid:
            return
        self._controller.publish_goal_select(gid)
        self._controller.publish_inspect_select(
            "goal",
            gid,
            label=gid,
            payload={"goal_id": gid},
        )

    def _on_goal_task_select(self, goal_id: str, task_id: str) -> None:
        """Plan task click → UI_GOAL_TASK_SELECT + inspect."""
        gid = str(goal_id).strip()
        tid = str(task_id).strip()
        if not tid:
            return
        self._controller.publish_goal_task_select(gid, tid)
        self._controller.publish_inspect_select(
            "plan_step",
            tid,
            label=tid,
            payload={"goal_id": gid, "task_id": tid, "step_id": tid},
        )

    def _on_brain_goal_select(self, goal_id: str) -> None:
        """Brain workspace goal click → UI_BRAIN_SELECT + inspect."""
        gid = str(goal_id).strip()
        if not gid:
            return
        self._controller.publish_brain_select(gid)
        self._on_goal_select(gid)

    def _on_goal_new(self, title: str, priority: int = 0) -> None:
        """Publish GOAL_SUBMIT_REQUEST for Hero New Goal (never lifecycle facts)."""
        self._controller.publish_goal_submit_request(title, priority=priority)

    def _on_approval_decide(
        self,
        check_id: str,
        granted: bool,
        permissions: tuple[str, ...],
        actor_type: str,
        actor_id: str,
    ) -> None:
        """Publish PERMISSION_CHECK_RESULT for Approve / Deny."""
        self._controller.publish_permission_result(
            check_id=check_id,
            granted=granted,
            permissions=permissions,
            actor_type=actor_type,
            actor_id=actor_id,
        )

    def _on_agent_cancel(self, agent_id: str, reason: str = "cancelled") -> None:
        """Publish AGENT_CANCEL_REQUEST for the contextual agent target."""
        self._controller.publish_agent_cancel_request(agent_id, reason=reason)

    def _on_execution_select(self, request_id: str) -> None:
        """Open execution detail and request timeline projection."""
        self._navigate("executions")
        self._controller.publish_execution_query(request_id)

    def _on_evidence_select(self, request_id: str) -> None:
        """Evidence claim click → UI_EVIDENCE_SELECT + inspect."""
        rid = str(request_id).strip()
        if not rid:
            return
        self._controller.publish_evidence_select(rid)
        snap = self._controller.snapshot()
        orch = snap.orchestration_run
        entry = orch
        if orch.request_id != rid:
            entry = next((e for e in orch.run_history if e.request_id == rid), orch)
        payload: dict[str, object] = {
            "request_id": rid,
            "claim": str(getattr(entry, "query", "") or getattr(entry, "intent", "") or rid),
            "truth": "valid" if getattr(entry, "truth_valid", False) else "failed",
            "receipt_id": str(getattr(entry, "receipt_id", "") or ""),
            "trace_id": str(getattr(entry, "trace_id", "") or ""),
            "span_id": str(getattr(entry, "span_id", "") or ""),
        }
        self._controller.publish_inspect_select(
            "evidence",
            rid,
            label=str(payload["claim"]),
            payload=payload,
        )

    def _on_operation_select(self, correlation_id: str) -> None:
        """Mission Control operation click → UI_OPERATION_SELECT + inspect."""
        cid = str(correlation_id).strip()
        if not cid:
            return
        self._controller.publish_operation_select(cid)
        snap = self._controller.snapshot()
        op = next(
            (o for o in snap.operation_library_index if o.correlation_id == cid),
            snap.active_operation,
        )
        payload: dict[str, object] = {"correlation_id": cid, "name": cid}
        if op is not None and op.correlation_id == cid:
            payload.update(
                {
                    "name": op.goal_title or cid,
                    "status": op.goal_status,
                    "goal_title": op.goal_title,
                    "goal_id": op.goal_id,
                }
            )
        self._controller.publish_inspect_select(
            "operation",
            cid,
            label=str(payload.get("name") or cid),
            payload=payload,
        )

    def _on_operation_scrub(self, index: int, step: dict[str, object]) -> None:
        """Timeline scrub → UI_OPERATION_SCRUB + execution timeline scrub + inspect."""
        snap = self._controller.snapshot()
        request_id = str(
            step.get("correlation_id")
            or snap.execution_scrubber.request_id
            or snap.orchestration_run.request_id
            or ""
        )
        self._controller.publish_operation_scrub(index, request_id=request_id)
        if request_id:
            self._controller.publish_execution_timeline_scrub(request_id, index)
        label = str(step.get("name") or f"step {index}")
        self._controller.publish_inspect_select(
            "execution_event",
            str(step.get("event_id") or step.get("entry_id") or f"scrub-{index}"),
            label=label,
            payload={
                "event_type": str(step.get("kind") or "timeline"),
                "status": str(step.get("status") or ""),
                "detail": label,
                "summary": label,
                "index": index,
                "request_id": request_id,
            },
        )

    def _on_execution_timeline_scrub(self, request_id: str, index: int) -> None:
        self._controller.publish_execution_timeline_scrub(request_id, index)

    def _on_workflow_run(self, workflow_id: str, steps: list[dict]) -> None:
        self._controller.publish_workflow_run(workflow_id, steps)

    def _on_workflow_node_select(self, node_id: str, label: str, workflow_id: str) -> None:
        self._controller.publish_workflow_node_select(
            node_id,
            workflow_id=workflow_id,
            label=label,
        )
        self._controller.publish_inspect_select(
            "workflow",
            node_id,
            label=label or node_id,
            payload={
                "workflow_id": workflow_id,
                "node_id": node_id,
            },
        )

    def _on_workflow_node_move(self, node_id: str, x: float, y: float) -> None:
        snap = self._controller.snapshot()
        workflow_id = snap.workflow_graph.workflow_id
        self._controller.publish_workflow_node_move(
            node_id,
            x,
            y,
            workflow_id=workflow_id,
        )

    def _on_workflow_timeline_scrub(self, index: int) -> None:
        snap = self._controller.snapshot()
        request_id = snap.workflow_graph.run_id or snap.active_workflow_run_id
        if request_id:
            self._controller.publish_execution_timeline_scrub(request_id, index)

    def _on_workflow_compare(self) -> None:
        snap = self._controller.snapshot()
        run_id = snap.workflow_graph.run_id or getattr(snap, "active_workflow_run_id", "")
        if not run_id:
            return
        self._navigate("executions")
        self._controller.publish_execution_query(run_id)

    def _on_automation_run(self, workflow_id: str) -> None:
        self._controller.publish_automation_run(workflow_id)

    def _on_automation_select_run(self, run_id: str, workflow_id: str) -> None:
        label = workflow_id.replace("-", " ").title() if workflow_id else run_id[:12]
        self._controller.publish_inspect_select(
            "workflow",
            run_id,
            label=label,
            payload={"run_id": run_id, "workflow_id": workflow_id},
        )

    def _on_automation_schedule_toggle(self, schedule_id: str) -> None:
        self._controller.publish_automation_schedule_toggle(schedule_id)

    def _on_automation_select_failure(self, run_id: str) -> None:
        snap = self._controller.snapshot()
        failure = next(
            (item for item in snap.automation_workspace.failures if item.run_id == run_id),
            None,
        )
        label = failure.title if failure is not None else run_id
        workflow_id = failure.workflow_id if failure is not None else ""
        self._controller.publish_automation_select(run_id, workflow_id=workflow_id, label=label)
        self._controller.publish_inspect_select(
            "workflow",
            run_id,
            label=label,
            payload={"run_id": run_id, "workflow_id": workflow_id},
        )

    def _on_automation_timeline_scrub(self, index: int) -> None:
        snap = self._controller.snapshot()
        run_id = snap.automation_workspace.selected_failure_run_id
        if run_id:
            self._controller.publish_execution_timeline_scrub(run_id, index)

    def _executions_view(self) -> "ExecutionsView | None":
        v = self._views.get("executions")
        return v if isinstance(v, ExecutionsView) else None

    def _goal_view(self) -> "GoalView | None":
        v = self._views.get("goals")
        return v if isinstance(v, GoalView) else None

    def _agents_view(self) -> "AgentsView | None":
        v = self._views.get("agents")
        return v if isinstance(v, AgentsView) else None

    def _approvals_view(self) -> "ApprovalsView | None":
        v = self._views.get("approvals")
        return v if isinstance(v, ApprovalsView) else None

    def _timeline_view(self) -> ExecutionTimelineView | None:
        v = self._views.get("timeline")
        return v if isinstance(v, ExecutionTimelineView) else None

    def _workflow_graph_view(self) -> WorkflowGraphView | None:
        v = self._views.get("workflow")
        return v if isinstance(v, WorkflowGraphView) else None

    def _automation_workspace_view(self) -> AutomationWorkspaceView | None:
        v = self._views.get("automation")
        return v if isinstance(v, AutomationWorkspaceView) else None

    def _providers_view(self) -> ProvidersView | None:
        v = self._views.get("providers")
        return v if isinstance(v, ProvidersView) else None

    def _capabilities_view(self) -> CapabilitiesView | None:
        v = self._views.get("capabilities")
        return v if isinstance(v, CapabilitiesView) else None

    def _artifacts_view(self) -> ArtifactsView | None:
        v = self._views.get("artifacts")
        return v if isinstance(v, ArtifactsView) else None
