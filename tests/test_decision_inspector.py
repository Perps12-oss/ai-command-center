from __future__ import annotations

import pytest

try:
    import tkinter as tk
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter unavailable: {exc}", allow_module_level=True)

try:
    _root = tk.Tk()
    _root.withdraw()
    _root.destroy()
except Exception as exc:  # pragma: no cover - environment specific
    pytest.skip(f"tkinter display unavailable: {exc}", allow_module_level=True)

from ai_command_center.domain.decision import Decision
from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.inspector import DecisionInspector, InspectorHost
from ai_command_center.ui.components.execution_badge import ExecutionBadge
from ai_command_center.ui.views.chat import response_action_strip as strip_module
from ai_command_center.ui.views.chat.response_action_strip import ResponseActionStrip


def test_decision_domain_to_inspect_payload() -> None:
    decision = Decision(
        reason="Approve file write",
        alternatives=("approve", "reject"),
        chosen="approve",
        affected_files=("src/main.py",),
    )
    payload = decision.to_inspect_payload(
        ref_id="dec-1",
        label="Write to src/main.py",
    )
    ref = InspectableRef.from_payload(payload)

    assert ref.kind == "decision"
    assert ref.ref_id == "dec-1"
    assert ref.label == "Write to src/main.py"
    assert ("reason", "Approve file write") in ref.payload
    assert ("chosen", "approve") in ref.payload
    assert ("alternatives", "approve, reject") in ref.payload
    assert ("affected_files", "src/main.py") in ref.payload


def test_decision_inspector_smoke_and_host_registration() -> None:
    try:
        root = tk.Tk()
        root.withdraw()
    except Exception as exc:
        pytest.skip(f"tkinter display unavailable: {exc}")
    try:
        decision = Decision(reason="Approve deployment")
        ref = InspectableRef.from_payload(
            decision.to_inspect_payload(ref_id="dec-1", label="Deploy to staging")
        )

        inspector = DecisionInspector(root)
        inspector.pack(fill="both", expand=True)
        inspector.update(ref)

        host = InspectorHost(root)
        host.pack(fill="both", expand=True)
        host.show(ref)
        root.update_idletasks()

        assert host._visible_widget is host._registry["decision"]
        assert host._title.cget("text") == "Deploy to staging"
    finally:
        root.destroy()


def test_response_action_strip_calls_on_inspect_select_with_kind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    try:
        root = tk.Tk()
        root.withdraw()
    except Exception as exc:
        pytest.skip(f"tkinter display unavailable: {exc}")
    selected: list[InspectableRef] = []

    def capture(ref: InspectableRef) -> None:
        selected.append(ref)

    try:
        strip = ResponseActionStrip(
            root,
            execution_id="exec-1",
            execution_index=3,
            artifact_count=2,
            decision_count=1,
            on_inspect_select=capture,
        )
        strip.pack()
        root.update_idletasks()

        pills = [w for w in strip.winfo_children() if isinstance(w, strip_module._ActionPill)]
        badges = [w for w in strip.winfo_children() if isinstance(w, ExecutionBadge)]
        assert len(pills) == 2
        assert len(badges) == 1

        for pill in pills:
            pill.invoke()
        badges[0].invoke()
        root.update_idletasks()

        kinds = sorted(ref.kind for ref in selected)
        assert kinds == ["artifact", "decision", "execution"]
        by_kind = {ref.kind: ref for ref in selected}
        assert by_kind["execution"].ref_id == "exec-1"
        assert by_kind["artifact"].kind == "artifact"
        assert by_kind["decision"].kind == "decision"
    finally:
        root.destroy()
