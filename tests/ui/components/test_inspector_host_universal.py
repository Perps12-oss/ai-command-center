"""Component tests for InspectorHost and the universal inspector registry."""

from __future__ import annotations

import pytest

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.core.state.inspector_state import resolve_inspect_navigate_view
from tests.ui.fake_ui import InspectorHost


@pytest.fixture
def inspector_host():
    """Return a fake-bound InspectorHost instance."""
    return InspectorHost(None)


_KINDS = [
    "message",
    "artifact",
    "provider",
    "decision",
    "goal",
    "task",
    "memory",
    "agent",
    "note",
    "world_node",
    "execution_event",
]


@pytest.mark.parametrize("kind", _KINDS)
def test_show_registered_kind_updates_title(inspector_host, kind):
    """Each registered kind can be shown without error."""
    ref = InspectableRef(kind=kind, ref_id="abc", label=f"A {kind}", payload=(("title", "test"),))
    inspector_host.show(ref)
    assert inspector_host._current_ref == ref
    assert inspector_host._title.cget("text") == f"A {kind}"


@pytest.mark.parametrize("kind", _KINDS)
def test_clear_returns_to_inspector_title(inspector_host, kind):
    """Clear resets the host back to the default empty state."""
    ref = InspectableRef(kind=kind, ref_id="abc", label=f"A {kind}")
    inspector_host.show(ref)
    inspector_host.clear()
    assert inspector_host._current_ref is None
    assert inspector_host._title.cget("text") == "Inspector"


def test_show_unknown_kind_shows_empty_hint(inspector_host):
    """Unknown kinds render the empty-hint view and still record the ref."""
    ref = InspectableRef(kind="unknown", ref_id="u1", label="Unknown")
    inspector_host.show(ref)
    assert inspector_host._current_ref == ref
    assert inspector_host._title.cget("text") == "Unknown"


def test_navigate_button_invokes_callback():
    """The header navigate arrow forwards the current ref to the callback."""
    seen = []

    def on_navigate(ref):
        seen.append(ref)

    host = InspectorHost(None, on_navigate=on_navigate)
    ref = InspectableRef(kind="goal", ref_id="g1", label="Goal One")
    host.show(ref)

    # Fake CTkButton stores state and command; invoke via the stored callback.
    btn = host._navigate_btn
    assert btn is not None
    assert btn.cget("state") == "normal"
    host._handle_navigate()
    assert len(seen) == 1
    assert seen[0] == ref


def test_navigate_button_disabled_when_empty():
    """The navigate button stays disabled until a ref is selected."""
    host = InspectorHost(None, on_navigate=lambda r: None)
    assert host._navigate_btn.cget("state") == "disabled"
    ref = InspectableRef(kind="task", ref_id="t1", label="Task One")
    host.show(ref)
    assert host._navigate_btn.cget("state") == "normal"
    host.clear()
    assert host._navigate_btn.cget("state") == "disabled"


@pytest.mark.parametrize(
    ("kind", "expected_view"),
    [
        ("message", "chat"),
        ("artifact", "artifacts"),
        ("provider", "providers"),
        ("execution", "executions"),
        ("decision", "chat"),
        ("goal", "goals"),
        ("task", "goals"),
        ("memory", "memory"),
        ("agent", "agents"),
        ("note", "notes"),
        ("world_node", "world_explorer"),
        ("execution_event", "executions"),
    ],
)
def test_resolve_inspect_navigate_view(kind, expected_view):
    """resolve_inspect_navigate_view maps every universal kind to a workspace."""
    assert resolve_inspect_navigate_view(kind) == expected_view
