"""AppState → widget projection for the command palette shell."""

from __future__ import annotations

from ai_command_center.core.state.inspector_state import resolve_inspect_navigate_view
from ai_command_center.core.state.artifact_state import artifacts_for_request
from ai_command_center.platform.secret_store import openai_api_key_configured
from ai_command_center.ui.components.permission_dialog import PermissionDialog
from ai_command_center.ui.design_system import theme_manager
from ai_command_center.ui.views.settings_view import SettingsView


class StateApplierMixin:
    """Applies AppState snapshots to shell widgets and catalog views."""

    def _queue_state_refresh(self) -> None:
        self._ui_queue.enqueue(self._apply_state)

    def _maybe_show_permission_dialog(self, snap) -> None:
        pending = getattr(snap, "pending_permission_check", None)
        if pending is None:
            self._shown_permission_check_id = None
            return
        if not pending.interactive:
            return
        shown_id = getattr(self, "_shown_permission_check_id", None)
        if shown_id == pending.check_id:
            return
        self._shown_permission_check_id = pending.check_id

        def on_result(granted: bool) -> None:
            self._controller.publish_permission_result(
                check_id=pending.check_id,
                granted=granted,
                permissions=list(pending.permissions),
                actor_type=pending.actor_type,
                actor_id=pending.actor_id,
            )

        PermissionDialog(
            self,
            check_id=pending.check_id,
            permissions=list(pending.permissions),
            actor_type=pending.actor_type,
            actor_id=pending.actor_id,
            summary=pending.summary,
            on_result=on_result,
        )

    def _apply_state(self) -> None:
        snap = self._controller.snapshot()
        diag = getattr(snap, "execution_inspector", None)
        self._maybe_show_permission_dialog(snap)
        extra = dict(snap.system_snapshot.extra)
        openai_online = bool(extra.get("openai_online", False))
        openai_configured = openai_api_key_configured(snap.settings.openai_api_key)
        self._top.update_llm_status(
            provider=snap.settings.provider,
            phase=snap.phase,
            model=snap.settings.default_model,
            ollama_online=snap.system_snapshot.ollama_online,
            openai_online=openai_online,
            openai_configured=openai_configured,
        )
        self._top.update_top_bar(snap)

        command_center = self._command_center_view()
        if command_center and hasattr(command_center, "apply_state"):
            command_center.apply_state(snap)

        if snap.chat_status == "streaming":
            self._last_terminal_chat_key = None
        self._overlay_mode = snap.settings.overlay_mode
        try:
            if self._overlay_mode == "compact":
                geom_key = ("compact", 0, 0)
            else:
                w = int(snap.settings.window_width)
                h = int(snap.settings.window_height)
                geom_key = ("window", w, h)
            if geom_key != getattr(self, "_applied_geometry_key", None):
                self._applied_geometry_key = geom_key
                if self._overlay_mode == "compact":
                    self._apply_overlay_geometry("compact", 0, 0)
                elif geom_key[1] >= 900 and geom_key[2] >= 560:
                    self.geometry(f"{geom_key[1]}x{geom_key[2]}")
        except ValueError:
            pass

        home = self._home_view()
        if home:
            home.update_stats(
                messages=self._msg_count,
                memories=self._memory_count,
                notes=self._note_count,
            )
            if snap.system_snapshot.ollama_online:
                home.update_ollama(True, snap.settings.default_model)
            else:
                home.update_ollama(False)

        chat = self._chat_view()
        if chat:
            chat.set_model(snap.settings.default_model)
            chat.update_entity_context(
                snap.chat_workspace_entity_id,
                snap.chat_workspace_entity_type,
                snap.chat_workspace_entity_title,
            )
            chat.update_context_bar(list(snap.chat_context_sources), int(snap.chat_token_estimate))
            if hasattr(chat, "update_inspector"):
                chat.update_inspector(
                    diag.execution_context if diag is not None else snap.execution_context
                )
            if hasattr(chat, "update_timeline"):
                execution_timeline = (
                    diag.execution_timeline if diag is not None else snap.execution_timeline
                )
                if execution_timeline.revision != getattr(
                    self, "_last_execution_timeline_revision", 0
                ):
                    chat.update_timeline(list(execution_timeline.events))
                    self._last_execution_timeline_revision = execution_timeline.revision
            if hasattr(chat, "show_inspector") and hasattr(chat, "clear_inspector"):
                if snap.inspector.revision != getattr(self, "_last_inspector_revision", 0):
                    if snap.inspector.selected is not None:
                        chat.show_inspector(snap.inspector.selected)
                    else:
                        chat.clear_inspector()
                    self._last_inspector_revision = snap.inspector.revision
            if hasattr(chat, "update_chat_execution_status"):
                status = "streaming" if snap.chat_streaming else str(snap.chat_status or "idle")
                chat.update_chat_execution_status(
                    status,
                    snap.settings.provider,
                    snap.settings.default_model,
                )

            if snap.chat_history_revision != self._last_chat_history_revision:
                messages = [
                    {"role": item.role, "content": item.content}
                    for item in snap.chat_history_messages
                ]
                chat.load_history(messages)
                self._last_chat_history_revision = snap.chat_history_revision

            if (
                snap.chat_streaming
                and snap.active_chat_request_id
                and snap.active_chat_request_id != self._last_started_request_id
            ):
                self._navigate("chat")
                chat = self._chat_view()
                if chat:
                    if snap.chat_started_user_text:
                        chat.show_user_message(snap.chat_started_user_text)
                    chat.begin_assistant(snap.active_chat_request_id)
                    self._last_started_request_id = snap.active_chat_request_id
                    self._last_stream_buffer_len = 0

            if (
                snap.chat_streaming
                and chat
                and snap.active_chat_request_id == self._last_started_request_id
            ):
                buffer_len = len(snap.chat_stream_buffer)
                if buffer_len > self._last_stream_buffer_len:
                    delta = snap.chat_stream_buffer[self._last_stream_buffer_len :]
                    chat.append_chunk(delta)
                    self._last_stream_buffer_len = buffer_len

            terminal_key = (str(snap.chat_status), str(snap.last_chat_request_id))
            if snap.chat_status == "complete":
                if terminal_key != self._last_terminal_chat_key and snap.last_chat_request_id:
                    chat.finish_assistant(str(snap.last_assistant_message))
                    if snap.last_chat_request_id not in self._completed_request_ids:
                        self._completed_request_ids.append(snap.last_chat_request_id)
                    self._last_started_request_id = None
                    self._last_stream_buffer_len = 0
                    self._top.update_status("ready", snap.settings.default_model)
                    self._last_terminal_chat_key = terminal_key
            elif snap.chat_status == "cancelled":
                if terminal_key != self._last_terminal_chat_key and snap.last_chat_request_id:
                    chat.show_cancelled()
                    if snap.last_chat_request_id not in self._completed_request_ids:
                        self._completed_request_ids.append(snap.last_chat_request_id)
                    self._last_started_request_id = None
                    self._last_stream_buffer_len = 0
                    self._last_terminal_chat_key = terminal_key
            elif snap.chat_status == "error":
                if terminal_key != self._last_terminal_chat_key and snap.last_chat_request_id:
                    self._navigate("chat")
                    chat = self._chat_view()
                    if chat:
                        chat.show_error(str(snap.last_chat_error or "Unknown error"))
                    if snap.last_chat_request_id not in self._completed_request_ids:
                        self._completed_request_ids.append(snap.last_chat_request_id)
                    self._last_started_request_id = None
                    self._last_stream_buffer_len = 0
                    self._top.update_status("error", snap.settings.default_model)
                    self._last_terminal_chat_key = terminal_key

            if chat and hasattr(chat, "update_artifact_stream"):
                req_id = snap.active_chat_request_id or snap.last_chat_request_id
                if req_id:
                    artifacts_snap = getattr(snap, "model_artifact", None)
                    artifact_catalog = (
                        artifacts_snap.recent_artifacts
                        if artifacts_snap is not None
                        else snap.recent_artifacts
                    )
                    scoped = artifacts_for_request(artifact_catalog, str(req_id))
                    chat.update_artifact_stream(str(req_id), scoped)

        if snap.inspector.navigate_revision != getattr(
            self, "_last_inspector_navigate_revision", 0
        ):
            target = snap.inspector.navigate_target
            if target is not None:
                view_id = resolve_inspect_navigate_view(target.kind)
                if view_id is not None:
                    self._navigate(view_id)
                    self._focus_inspect_navigate_target(target)
            self._last_inspector_navigate_revision = snap.inspector.navigate_revision

        timeline = self._timeline_view()
        if timeline and hasattr(timeline, "apply_state"):
            if snap.execution_timeline.revision != getattr(
                self, "_last_execution_timeline_view_revision", 0
            ):
                timeline.apply_state(list(snap.execution_timeline.events))
                self._last_execution_timeline_view_revision = snap.execution_timeline.revision

        try:
            theme_name = snap.settings.theme
            alpha = snap.settings.window_alpha
            if (
                theme_name != getattr(self, "_applied_theme_name", None)
                or alpha != getattr(self, "_applied_alpha", None)
            ):
                self._applied_theme_name = theme_name
                self._applied_alpha = alpha
                theme_manager.apply(
                    self,
                    theme_name=theme_name,
                    alpha=alpha,
                )
        except Exception:
            pass

        self._apply_catalog_views(snap)
        self._apply_settings_projection(snap)
        self._apply_execution_timeline(snap)
        self._apply_workflow_graph(snap)
        self._apply_automation_workspace(snap)

    def _apply_settings_projection(self, snap) -> None:
        """Keep SettingsView in sync when settings change off-page."""
        version = int(getattr(snap, "settings_version", 0))
        if version == getattr(self, "_last_settings_version", -1):
            return
        self._last_settings_version = version
        settings_view = self._views.get("settings")
        if isinstance(settings_view, SettingsView):
            settings_view.load_from_snapshot(snap.settings)

    def _apply_automation_workspace(self, snap) -> None:
        automation = self._automation_workspace_view()
        if automation is None or not hasattr(automation, "apply_state"):
            return
        workspace = snap.automation_workspace
        if workspace.revision != getattr(self, "_last_automation_workspace_revision", 0):
            automation.apply_state(workspace)
            self._last_automation_workspace_revision = workspace.revision
        if snap.inspector.revision != getattr(self, "_last_automation_inspector_revision", 0):
            if snap.inspector.selected is not None and snap.inspector.selected.kind == "workflow":
                automation.show_inspector(snap.inspector.selected)
            else:
                automation.clear_inspector()
            self._last_automation_inspector_revision = snap.inspector.revision

    def _apply_workflow_graph(self, snap) -> None:
        """Project workflow_graph into WorkflowGraphView and inspector dock."""
        workflow = self._workflow_graph_view()
        if workflow is None or not hasattr(workflow, "apply_state"):
            return
        graph = snap.workflow_graph
        if graph.revision != getattr(self, "_last_workflow_graph_revision", 0):
            workflow.apply_state(graph)
            self._last_workflow_graph_revision = graph.revision
        if snap.inspector.revision != getattr(self, "_last_workflow_inspector_revision", 0):
            if snap.inspector.selected is not None and snap.inspector.selected.kind == "workflow":
                workflow.show_inspector(snap.inspector.selected)
            else:
                workflow.clear_inspector()
            self._last_workflow_inspector_revision = snap.inspector.revision

    def _apply_execution_timeline(self, snap) -> None:
        """Project execution_scrubber into ExecutionsView detail scrubber."""
        executions = self._executions_view()
        if executions is None or not hasattr(executions, "apply_timeline"):
            return
        diag = getattr(snap, "execution_inspector", None)
        timeline = diag.execution_scrubber if diag is not None else snap.execution_scrubber
        if not timeline.request_id:
            return
        key = (
            timeline.request_id,
            timeline.scrub_index,
            tuple(event.event_id for event in timeline.events),
            timeline.source,
        )
        if key == getattr(self, "_last_execution_timeline_key", None):
            return
        self._last_execution_timeline_key = key

        steps: list[dict] = []
        labels: list[str] = []
        for event in timeline.events:
            labels.append(event.event_type)
            steps.append(
                {
                    "name": event.scope or event.event_type.split(".")[-1] or event.event_type,
                    "status": "ok",
                    "duration_ms": 0.0,
                    "detail": dict(event.payload),
                }
            )

        spans: list[dict] = []
        execution_context = (
            diag.execution_context if diag is not None else snap.execution_context
        )
        if execution_context.request_id == timeline.request_id:
            spans = [
                {
                    "span_id": span.span_id,
                    "parent_id": span.parent_id,
                    "name": span.name,
                    "kind": span.kind,
                    "status": span.status,
                    "duration_ms": span.duration_ms,
                    "started_at": span.started_at,
                    "attributes": dict(span.attributes),
                }
                for span in execution_context.trace_spans
            ]
            if not steps:
                for span in execution_context.trace_spans:
                    labels.append(span.name)
                    steps.append(
                        {
                            "name": span.name,
                            "status": span.status,
                            "duration_ms": span.duration_ms,
                            "detail": dict(span.attributes),
                        }
                    )

        executions.apply_timeline(
            request_id=timeline.request_id,
            timeline_steps=steps,
            scrub_labels=labels,
            scrub_index=timeline.scrub_index,
            timeline_source=timeline.source,
            spans=spans,
        )

    def _catalog_fingerprint(self, snap) -> tuple:
        """Fields that drive catalog view rebuilds (excludes polling system metrics)."""
        return (
            snap.memory_catalog,
            snap.memory_selected,
            snap.notes_catalog,
            snap.note_selected,
            snap.plugin_catalog,
            snap.errors,
            snap.agent_runs,
            snap.workflow_runs,
            snap.workspace_os,
            snap.execution_runs,
            snap.provider_health_map,
            snap.runtime_capability_providers,
            snap.capability_lifecycle,
            getattr(snap, "model_artifact", None),
            getattr(snap.execution_context, "artifacts", ()),
        )

    def _apply_catalog_views(self, snap) -> None:
        """Render Memory, Notes, Plugins, and System views from AppState."""
        fingerprint = self._catalog_fingerprint(snap)
        if fingerprint == getattr(self, "_last_catalog_fingerprint", None):
            system = self._system_view()
            if system:
                system.apply_system_snapshot(snap.system_snapshot)
            return
        self._last_catalog_fingerprint = fingerprint
        memory = self._memory_view()
        if memory:
            memory.load_from_appstate(snap)
            memory.update_injection_indicator(snap.memory_selected)

        notes = self._notes_view()
        if notes:
            notes.load_from_appstate(snap)

        plugins = self._plugins_view()
        if plugins:
            plugins.load_from_appstate(snap)

        system = self._system_view()
        if system:
            system.apply_system_snapshot(snap.system_snapshot)
            if snap.errors:
                system.load_errors(snap.errors)
            system.load_from_appstate(snap)

        workspace = self._workspace_view()
        if workspace:
            workspace.load_from_appstate(snap)

        executions = self._executions_view()
        if executions and hasattr(executions, "apply_state"):
            executions.apply_state(list(snap.execution_runs))

        providers = self._providers_view()
        if providers and hasattr(providers, "apply_state"):
            providers.apply_state(snap.provider_health_map, snap.runtime_capability_providers)

        capabilities = self._capabilities_view()
        if capabilities and hasattr(capabilities, "apply_state"):
            capabilities.apply_state(snap.capability_lifecycle)

        artifacts = self._artifacts_view()
        if artifacts and hasattr(artifacts, "set_artifacts"):
            artifacts_snap = getattr(snap, "model_artifact", None)
            artifact_catalog = (
                artifacts_snap.recent_artifacts
                if artifacts_snap is not None
                else snap.recent_artifacts
            )
            artifacts.set_artifacts(artifact_catalog)
        elif artifacts and hasattr(artifacts, "apply_state"):
            artifacts_snap = getattr(snap, "model_artifact", None)
            artifact_catalog = (
                artifacts_snap.recent_artifacts
                if artifacts_snap is not None
                else snap.recent_artifacts
            )
            artifacts.apply_state(artifact_catalog)

        home = self._home_view()
        if home:
            if snap.chat_history_count:
                home.update_stats(
                    messages=snap.chat_history_count,
                    memories=self._memory_count,
                    notes=self._note_count,
                )
            active_exec = sum(
                1 for r in snap.execution_runs
                if str(getattr(r, "source", "")) == "orchestration"
            )
            provider_health = "healthy" if snap.provider_health_map else ""
            artifact_catalog = (
                snap.model_artifact.recent_artifacts
                if getattr(snap, "model_artifact", None) is not None
                else snap.recent_artifacts
            )
            artifact_count = len(artifact_catalog) or len(
                getattr(snap.execution_context, "artifacts", ())
            )
            pending = 1 if snap.pending_permission_check else 0
            if hasattr(home, "update_execution_summary"):
                home.update_execution_summary(
                    active_count=active_exec,
                    provider_health=provider_health,
                    artifact_count=artifact_count,
                    pending_approvals=pending,
                )
