"""ExecutionTimelineScrubber must not ZeroDivisionError on empty/single timelines."""

from __future__ import annotations

import pytest

try:
    import tkinter as tk
except Exception as exc:  # pragma: no cover
    pytest.skip(f"tkinter unavailable: {exc}", allow_module_level=True)

try:
    _probe = tk.Tk()
    _probe.withdraw()
    _probe.destroy()
except Exception as exc:  # pragma: no cover
    pytest.skip(f"tkinter display unavailable: {exc}", allow_module_level=True)

import customtkinter as ctk

from ai_command_center.ui.components.docks.execution_timeline_dock import (
    ExecutionTimelineDock,
)
from ai_command_center.ui.components.execution_timeline_scrubber import (
    ExecutionTimelineScrubber,
)


@pytest.fixture
def root():
    app = ctk.CTk()
    app.withdraw()
    yield app
    try:
        app.destroy()
    except Exception:
        pass


@pytest.mark.parametrize("labels", [[], ["only-one"]])
def test_set_timeline_empty_or_single_does_not_zerodiv(root, labels) -> None:
    scrubber = ExecutionTimelineScrubber(root)
    scrubber.set_timeline(labels, active_index=0)
    assert scrubber._slider._number_of_steps >= 1
    # Re-entrant set must stay safe.
    scrubber.set_timeline(labels, active_index=99)


def test_set_timeline_recovers_from_zero_steps(root) -> None:
    """Regression: CTkSlider.set divides by number_of_steps — never leave 0."""
    scrubber = ExecutionTimelineScrubber(root)
    scrubber._slider.configure(from_=0, to=1, number_of_steps=0)
    scrubber._safe_slider_set(0)
    assert scrubber._slider._number_of_steps >= 1


def test_set_timeline_multi_event_scrubs(root) -> None:
    seen: list[int] = []
    scrubber = ExecutionTimelineScrubber(root, on_scrub=seen.append)
    scrubber.set_timeline(["a", "b", "c"], active_index=1)
    assert scrubber._index == 1
    scrubber._emit_scrub(2)
    assert seen == [2]
    assert scrubber._index == 2


def test_dock_render_empty_and_single_step(root) -> None:
    dock = ExecutionTimelineDock(root)
    dock.render([], scrub_labels=[], scrub_index=0)
    dock.render(
        [{"name": "one", "status": "ok"}],
        scrub_labels=["one"],
        scrub_index=0,
    )
    dock.render(
        [
            {"name": "a", "status": "ok"},
            {"name": "b", "status": "ok"},
        ],
        scrub_labels=["a", "b"],
        scrub_index=1,
    )


def test_dock_render_identical_is_noop(root) -> None:
    dock = ExecutionTimelineDock(root)
    steps = [{"name": "a", "status": "ok", "duration_ms": 0.0}]
    dock.render(steps, scrub_labels=["a"], scrub_index=0)
    fp = dock._render_fingerprint
    dock.render(steps, scrub_labels=["a"], scrub_index=0)
    assert dock._render_fingerprint == fp
