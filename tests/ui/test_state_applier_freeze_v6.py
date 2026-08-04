"""Unit tests for phased / throttled StateApplierMixin behaviour (freeze_fix=v6)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from ai_command_center.ui.shell.state_applier import StateApplierMixin, _CATALOG_VIEWS


class _SyncUIQueue:
    def __init__(self) -> None:
        self.calls: list = []

    def enqueue(self, callback) -> None:
        self.calls.append(callback)
        callback()


class _Harness(StateApplierMixin):
    def __init__(self) -> None:
        self._ui_queue = _SyncUIQueue()
        self._controller = MagicMock()
        self._top = MagicMock()
        self._context_bar = MagicMock()
        self._sidebar = MagicMock()
        self._views: dict = {}
        self._current_view = "chat"
        self._state_refresh_enqueued = False
        self._state_refresh_pending = False
        self._last_apply_state_time = 0.0
        self._min_frame_interval = 0.033
        self._frame_governor_scheduled = False
        self._stream_chunk_buffer = ""
        self._stream_chunks_since_update = 0
        self._stream_batch_threshold = 3
        self._last_stream_buffer_len = 0
        self._last_started_request_id = "req-1"
        self._last_stream_fingerprint = None
        self._last_snapshot_for_apply = None
        self._apply_pipeline_started = None
        self._catalog_refresh_deferred = False
        self._last_catalog_fingerprint = None
        self._completed_request_ids = []
        self._last_terminal_chat_key = None
        self._last_chat_history_revision = 0
        self._chat = MagicMock()
        self._scheduled: list[tuple[int, object]] = []

    def after(self, delay_ms, callback):  # noqa: ANN001
        self._scheduled.append((delay_ms, callback))

    def _chat_view(self):
        return self._chat

    def _command_center_view(self):
        return None

    def _goal_view(self):
        return None

    def _brain_view(self):
        return None

    def _agents_view(self):
        return None

    def _approvals_view(self):
        return None

    def _world_explorer_view(self):
        return None

    def _graph_workspace_view(self):
        return None

    def _insights_view(self):
        return None

    def _evidence_view(self):
        return None

    def _operations_view(self):
        return None

    def _executions_view(self):
        return None

    def _timeline_view(self):
        return None

    def _memory_view(self):
        return None

    def _notes_view(self):
        return None

    def _plugins_view(self):
        return None

    def _system_view(self):
        return None

    def _workspace_view(self):
        return None

    def _providers_view(self):
        return None

    def _capabilities_view(self):
        return None

    def _artifacts_view(self):
        return None

    def _workflow_graph_view(self):
        return None

    def _automation_workspace_view(self):
        return None

    def _show_view(self, _view_id: str) -> None:
        return None

    def _apply_overlay_geometry(self, *_a, **_k) -> None:
        return None

    def _focus_inspect_navigate_target(self, *_a, **_k) -> None:
        return None

    def geometry(self, *_a, **_k) -> None:
        return None


def _stream_snap(*, buffer: str = "abc", streaming: bool = True) -> SimpleNamespace:
    settings = SimpleNamespace(
        provider="ollama",
        default_model="m",
        openai_api_key="",
        overlay_mode="palette",
        window_width=1100,
        window_height=700,
        theme="dark",
        window_alpha=1.0,
    )
    return SimpleNamespace(
        chat_streaming=streaming,
        chat_stream_buffer=buffer,
        chat_status="streaming" if streaming else "idle",
        active_chat_request_id="req-1",
        last_chat_request_id=None,
        chat_started_user_text="",
        last_assistant_message="",
        last_chat_error="",
        settings_version=1,
        phase="ready",
        chat_history_revision=0,
        chat_history_messages=(),
        chat_workspace_entity_id=None,
        chat_workspace_entity_type=None,
        chat_workspace_entity_title=None,
        chat_context_sources=(),
        chat_token_estimate=0,
        system_snapshot=SimpleNamespace(ollama_online=True, extra={}),
        settings=settings,
        inspector=SimpleNamespace(revision=0, navigate_revision=0, selected=None, navigate_target=None),
        execution_inspector=None,
        execution_context=SimpleNamespace(request_id="", trace_spans=()),
        execution_timeline=SimpleNamespace(events=(), revision=0),
        execution_scrubber=SimpleNamespace(request_id="", scrub_index=0, events=(), source=""),
        permission_snapshot=None,
        agent_pipeline=None,
        pending_permission_check=None,
        recent_artifacts=(),
        model_artifact=None,
        automation_workspace=SimpleNamespace(revision=0),
        workflow_graph=SimpleNamespace(revision=0),
        memory_catalog=(),
        memory_selected=None,
        notes_catalog=(),
        note_selected=None,
        plugin_catalog=(),
        errors=(),
        agent_runs=(),
        workflow_runs=(),
        workspace_os=None,
        execution_runs=(),
        provider_health_map={},
        runtime_capability_providers=(),
        capability_lifecycle=None,
    )


def test_stream_throttle_batches_appends() -> None:
    h = _Harness()
    snap = _stream_snap(buffer="abcdefghij")
    h._last_stream_fingerprint = h._stream_fingerprint(snap)
    h._controller.snapshot.return_value = snap

    # Three stream-only applies with growing buffer → one batched append at threshold.
    for end in (2, 5, 8):
        snap.chat_stream_buffer = "abcdefghij"[:end]
        assert h._try_apply_stream_only(snap) is True

    # threshold=3 → after third chunk update, append fires once with accumulated text
    assert h._chat.append_chunk.call_count == 1
    assert h._chat.append_chunk.call_args[0][0] == "abcdefgh"


def test_terminal_flush_drains_throttled_tail_before_finish() -> None:
    """Below-threshold buffered chunks must still reach the widget on complete."""
    h = _Harness()
    snap = _stream_snap(buffer="ab")
    h._last_stream_fingerprint = h._stream_fingerprint(snap)
    h._controller.snapshot.return_value = snap

    assert h._try_apply_stream_only(snap) is True
    snap.chat_stream_buffer = "abcd"
    assert h._try_apply_stream_only(snap) is True
    # 2 chunks < threshold 3 → still buffered, no widget append yet
    assert h._chat.append_chunk.call_count == 0
    assert h._stream_chunk_buffer == "abcd"

    done = _stream_snap(buffer="abcd", streaming=False)
    done.chat_status = "complete"
    done.last_chat_request_id = "req-1"
    done.last_assistant_message = "abcd"
    done.active_chat_request_id = None
    h._controller.snapshot.return_value = done
    h._last_apply_state_time = 0.0
    h._queue_state_refresh()

    flushed = "".join(c.args[0] for c in h._chat.append_chunk.call_args_list)
    assert flushed == "abcd"
    h._chat.finish_assistant.assert_called_once_with("abcd")
    assert h._stream_chunk_buffer == ""
    assert h._stream_chunks_since_update == 0


def test_frame_governor_defers_rapid_refresh() -> None:
    h = _Harness()
    h._last_apply_state_time = __import__("time").monotonic()
    h._queue_state_refresh()
    assert h._state_refresh_pending is True
    assert h._state_refresh_enqueued is False
    assert len(h._scheduled) == 1


def test_catalog_deferred_while_on_chat() -> None:
    h = _Harness()
    h._current_view = "chat"
    snap = _stream_snap(streaming=True)
    h._apply_catalog_views(snap)
    assert h._catalog_refresh_deferred is True
    assert "chat" not in _CATALOG_VIEWS


def test_catalog_deferred_when_idle_off_catalog() -> None:
    """G4: deferral is off-catalog policy, not stream-storm-only."""
    h = _Harness()
    h._current_view = "command_center"
    snap = _stream_snap(streaming=False)
    snap.chat_status = "idle"
    h._apply_catalog_views(snap)
    assert h._catalog_refresh_deferred is True


def test_apply_state_shim_delegates_to_queue_refresh() -> None:
    """G3: direct _apply_state() must use the same coalesce path."""
    h = _Harness()
    snap = _stream_snap(buffer="hello")
    h._last_stream_fingerprint = h._stream_fingerprint(snap)
    h._controller.snapshot.return_value = snap
    h._apply_state()
    assert h._top.update_top_bar.call_count == 0
    assert h._state_refresh_enqueued is False


def test_phased_apply_stream_only_skips_phase_2() -> None:
    h = _Harness()
    snap = _stream_snap(buffer="hello")
    h._last_stream_fingerprint = h._stream_fingerprint(snap)
    h._controller.snapshot.return_value = snap
    h._queue_state_refresh()
    # Sync queue runs phase_1; stream-only should finish without top-bar updates.
    assert h._top.update_top_bar.call_count == 0
    assert h._state_refresh_enqueued is False
