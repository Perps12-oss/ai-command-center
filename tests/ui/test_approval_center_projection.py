"""Projection tests for Phase 11E Approval Center workspace."""

from __future__ import annotations

from pathlib import Path

from ai_command_center.core.app_state import AppState
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import PERMISSION_CHECK_RESULT
from ai_command_center.core.app_state import AppStateStore
from ai_command_center.domain.execution_library_snapshot import (
    ExecutionLibrarySnapshot,
    ExecutionPlanSnapshot,
    ExecutionStepSnapshot,
)
from ai_command_center.domain.permission_check_snapshot import (
    PendingCheck,
    PermissionCheckSnapshot,
    ResolvedCheck,
)
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.design_system import theme_v2 as T
from ai_command_center.ui.views.approval_center.risk_classification import (
    classify_approval_risk,
)
from tests.ui.fake_ui import ApprovalsView

ROOT = Path(__file__).resolve().parents[2]


def _pending(**kwargs: object) -> PendingCheck:
    defaults = dict(
        check_id="chk-1",
        permissions=("launch_tool",),
        actor_type="agent",
        actor_id="agent-1",
        summary="Agent spawn requires: launch_tool",
    )
    defaults.update(kwargs)
    return PendingCheck(**defaults)  # type: ignore[arg-type]


def _sample_snap(
    *,
    pending: bool = True,
    granted: int = 2,
    denied: int = 1,
    with_execution_risk: bool = False,
) -> AppState:
    resolved = (
        ResolvedCheck(
            check_id="chk-old",
            actor_id="agent-0",
            granted=True,
            summary="Earlier grant",
        ),
        ResolvedCheck(
            check_id="chk-older",
            actor_id="agent-z",
            granted=False,
            summary="Earlier deny",
        ),
    )
    permission = PermissionCheckSnapshot(
        pending=_pending() if pending else None,
        resolved=resolved,
        total_requested=granted + denied + (1 if pending else 0),
        total_granted=granted,
        total_denied=denied,
    )
    library = ExecutionLibrarySnapshot()
    if with_execution_risk:
        library = ExecutionLibrarySnapshot(
            active_plan=ExecutionPlanSnapshot(
                run_id="run-1",
                request_id="req-1",
                status="awaiting_approval",
                current_step_id="s1",
                steps=(
                    ExecutionStepSnapshot(
                        step_id="s1",
                        run_id="run-1",
                        capability="git_push",
                        risk="high",
                        status="awaiting_approval",
                    ),
                ),
            )
        )
    return AppState(permission_snapshot=permission, execution_library=library)


def test_hero_metrics_and_review_next() -> None:
    view = ApprovalsView(None)
    view.apply_state(_sample_snap(pending=True, granted=2, denied=1))
    metrics = view._metrics.cget("text")
    assert "1 pending" in metrics
    assert "2 granted" in metrics
    assert "1 denied" in metrics
    assert "Last: granted" in metrics  # resolved[0] ordering only
    assert view._hero_action.cget("state") == "normal"
    view._hero_action.invoke()
    assert view._focused_check_id == "chk-1"


def test_hero_last_decision_no_history() -> None:
    view = ApprovalsView(None)
    empty = AppState(
        permission_snapshot=PermissionCheckSnapshot(
            pending=_pending(),
            resolved=(),
            total_requested=1,
        )
    )
    view.apply_state(empty)
    assert "No decisions recorded" in view._metrics.cget("text")


def test_review_next_disabled_when_empty() -> None:
    view = ApprovalsView(None)
    view.apply_state(_sample_snap(pending=False))
    assert view._hero_action.cget("state") == "disabled"
    assert "No pending" in view._hero_hint.cget("text")


def test_pending_queue_renders_and_empty_state() -> None:
    view = ApprovalsView(None)
    view.apply_state(_sample_snap(pending=True))
    assert view._queue._badge.cget("text") == "1 pending"
    texts: list[str] = []
    for child in view._queue._body.winfo_children():
        for nested in getattr(child, "winfo_children", lambda: [])():
            for leaf in getattr(nested, "winfo_children", lambda: [])():
                if hasattr(leaf, "cget"):
                    try:
                        texts.append(str(leaf.cget("text")))
                    except Exception:
                        pass
    joined = "\n".join(texts)
    assert "chk-1" in joined
    assert "launch_tool" in joined

    view.apply_state(_sample_snap(pending=False))
    empty_texts = []
    for child in view._queue._body.winfo_children():
        if hasattr(child, "cget"):
            try:
                empty_texts.append(str(child.cget("text")))
            except Exception:
                pass
    assert any("No pending approvals" in t for t in empty_texts)


def test_risk_execution_capability_and_unknown() -> None:
    exec_view = classify_approval_risk(
        _pending(),
        execution_library=_sample_snap(with_execution_risk=True).execution_library,
    )
    assert exec_view.tier == "high"
    assert exec_view.source == "execution_step"
    assert "git_push" in exec_view.reason or "s1" in exec_view.reason

    cap_view = classify_approval_risk(_pending(permissions=("launch_tool",)))
    assert cap_view.tier == "high"
    assert cap_view.source == "capability_map"
    assert "launch_tool" in cap_view.reason

    unknown = classify_approval_risk(None)
    assert unknown.tier == "unknown"
    assert unknown.source == "unknown"
    assert "No execution step risk" in unknown.reason

    view = ApprovalsView(None)
    view.apply_state(_sample_snap(with_execution_risk=True))
    risk_texts: list[str] = []
    for child in view._risk._body.winfo_children():
        for nested in getattr(child, "winfo_children", lambda: [])():
            if hasattr(nested, "cget"):
                try:
                    risk_texts.append(str(nested.cget("text")))
                except Exception:
                    pass
    assert any("HIGH" in t for t in risk_texts)
    assert any("execution_step" in t for t in risk_texts)


def test_decision_history_projection() -> None:
    view = ApprovalsView(None)
    view.apply_state(_sample_snap())
    assert view._history._count.cget("text") == "2"
    texts: list[str] = []
    for child in view._history._body.winfo_children():
        for nested in getattr(child, "winfo_children", lambda: [])():
            if hasattr(nested, "cget"):
                try:
                    texts.append(str(nested.cget("text")))
                except Exception:
                    pass
    joined = "\n".join(texts)
    assert "GRANTED" in joined
    assert "chk-old" in joined
    assert "DENIED" in joined


def test_statistics_counts() -> None:
    view = ApprovalsView(None)
    view.apply_state(_sample_snap(pending=True, granted=2, denied=1))
    assert view._stats._requested.cget("text") == "4"
    assert view._stats._granted.cget("text") == "2"
    assert view._stats._denied.cget("text") == "1"
    assert view._stats._pending.cget("text") == "1"


def test_approve_and_deny_publish_permission_check_result() -> None:
    bus = EventBus()
    ctrl = UIController(bus, AppStateStore(bus), on_state=lambda: None)
    seen: list[dict] = []
    bus.subscribe(PERMISSION_CHECK_RESULT, lambda e: seen.append(dict(e.payload)))

    decided: list[tuple] = []
    view = ApprovalsView(
        None,
        on_decide=lambda cid, granted, perms, atype, aid: decided.append(
            (cid, granted, perms, atype, aid)
        ),
    )
    view.apply_state(_sample_snap(pending=True))
    view._queue._approve_btn.invoke()
    assert decided[0][0] == "chk-1"
    assert decided[0][1] is True

    view._queue._deny_btn.invoke()
    assert decided[1][1] is False

    ctrl.publish_permission_result(
        check_id="chk-1",
        granted=True,
        permissions=["launch_tool"],
        actor_type="agent",
        actor_id="agent-1",
    )
    assert seen[-1]["check_id"] == "chk-1"
    assert seen[-1]["granted"] is True


def test_approval_orange_token_used() -> None:
    files = [
        ROOT / "ai_command_center/ui/views/approvals_view.py",
        ROOT / "ai_command_center/ui/views/approval_center/pending_queue_panel.py",
        ROOT / "ai_command_center/ui/views/approval_center/risk_classification_panel.py",
        ROOT / "ai_command_center/ui/views/approval_center/decision_history_panel.py",
        ROOT / "ai_command_center/ui/views/approval_center/approval_statistics_panel.py",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "APPROVAL_ORANGE" in text, path.name
        assert "#FF9800" not in text
    assert T.APPROVAL_ORANGE == "#FF9800"


def test_no_repo_or_service_imports() -> None:
    files = list(
        (ROOT / "ai_command_center/ui/views/approval_center").glob("*.py")
    ) + [ROOT / "ai_command_center/ui/views/approvals_view.py"]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "ai_command_center.repositories" not in text
        assert "ai_command_center.services" not in text
        assert "add_listener" not in text
