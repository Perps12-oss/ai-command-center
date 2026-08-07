"""UI freeze closeout — executions/command-center apply fingerprints."""

from __future__ import annotations

import pytest

from ai_command_center.core.app_state import AppState
from ai_command_center.domain.execution_library_snapshot import (
    ExecutionLibrarySnapshot,
    ExecutionPlanSnapshot,
    ExecutionRunEntry,
)
from ai_command_center.ui.views.execution_center.execution_list_panel import (
    _format_duration,
)
from ai_command_center.ui.views.executions_view import ExecutionsView

try:
    import tkinter as tk
except Exception as exc:  # pragma: no cover
    tk = None  # type: ignore[assignment]
    _TK_SKIP = f"tkinter unavailable: {exc}"
else:
    try:
        _probe = tk.Tk()
        _probe.withdraw()
        _probe.destroy()
        _TK_SKIP = ""
    except Exception as exc:  # pragma: no cover
        _TK_SKIP = f"tkinter display unavailable: {exc}"


def test_format_duration_uses_five_second_buckets() -> None:
    now = 1_000.0
    assert _format_duration(999.0, now=now) == "0s"
    assert _format_duration(994.0, now=now) == "5s"
    assert _format_duration(940.0, now=now) == "1m"


def _snap(*, status: str = "complete", run_id: str = "r1") -> AppState:
    entry = ExecutionRunEntry(
        run_id=run_id,
        request_id=run_id,
        status=status,
        source="chat",
        created_at=100.0,
        summary="demo",
    )
    lib = ExecutionLibrarySnapshot(
        run_history=(entry,),
        total_runs=1,
        active_plan=ExecutionPlanSnapshot(),
    )
    return AppState(execution_library=lib)


def test_executions_fingerprint_ignores_identical_ticks() -> None:
    a = _snap()
    b = _snap()
    assert ExecutionsView._fingerprint(a, "") == ExecutionsView._fingerprint(b, "")
    c = _snap(status="failed")
    assert ExecutionsView._fingerprint(a, "") != ExecutionsView._fingerprint(c, "")
    assert ExecutionsView._fingerprint(a, "r1") != ExecutionsView._fingerprint(a, "")


@pytest.mark.skipif(bool(_TK_SKIP), reason=_TK_SKIP or "tk required")
def test_execution_center_panels_fingerprint_skip_identical_rebuilds() -> None:
    import customtkinter as ctk

    from ai_command_center.ui.views.execution_center.execution_detail_panel import (
        ExecutionDetailPanel,
    )
    from ai_command_center.ui.views.execution_center.execution_timeline_panel import (
        ExecutionTimelinePanel,
    )
    from ai_command_center.ui.views.execution_center.receipt_viewer_panel import (
        ReceiptViewerPanel,
    )
    from ai_command_center.ui.views.execution_center.truth_validation_panel import (
        TruthValidationPanel,
    )

    root = ctk.CTk()
    root.withdraw()
    try:
        snap = _snap()
        timeline = ExecutionTimelinePanel(root)
        detail = ExecutionDetailPanel(root)
        receipt = ReceiptViewerPanel(root)
        truth = TruthValidationPanel(root)

        timeline.apply_snapshot(snap, selected_request_id="r1")
        detail.apply_snapshot(snap, selected_request_id="r1")
        receipt.apply_snapshot(snap, selected_request_id="r1")
        truth.apply_snapshot(snap, selected_request_id="r1")

        t_fp = timeline._snapshot_fingerprint
        d_fp = detail._snapshot_fingerprint
        r_fp = receipt._snapshot_fingerprint
        v_fp = truth._snapshot_fingerprint

        timeline.apply_snapshot(snap, selected_request_id="r1")
        detail.apply_snapshot(snap, selected_request_id="r1")
        receipt.apply_snapshot(snap, selected_request_id="r1")
        truth.apply_snapshot(snap, selected_request_id="r1")

        assert timeline._snapshot_fingerprint == t_fp
        assert detail._snapshot_fingerprint == d_fp
        assert receipt._snapshot_fingerprint == r_fp
        assert truth._snapshot_fingerprint == v_fp
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def test_apply_execution_timeline_skips_off_executions_view() -> None:
    """Scrubber projection must not run Tk work when Executions is hidden."""

    class _Applier:
        _current_view = "chat"
        called = False

        def _executions_view(self):
            self.called = True
            return object()

        def _apply_execution_timeline(self, snap):
            from ai_command_center.ui.shell.state_applier import StateApplierMixin

            return StateApplierMixin._apply_execution_timeline(self, snap)

    applier = _Applier()
    applier._apply_execution_timeline(AppState())
    assert applier.called is False
    applier._current_view = "executions"
    applier._apply_execution_timeline(AppState())
    # request_id empty → returns after view gate + executions lookup
    assert applier.called is True
