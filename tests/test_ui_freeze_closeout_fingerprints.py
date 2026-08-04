"""UI freeze closeout — executions/command-center apply fingerprints."""

from __future__ import annotations

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
