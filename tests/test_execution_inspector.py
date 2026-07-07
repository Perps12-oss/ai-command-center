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

from ai_command_center.core.state.execution_state import ArtifactItem, ExecutionContext, SpanItem
from ai_command_center.ui.components.inspector import CollapsibleSection, ExecutionInspector, InspectorHost


def test_execution_inspector_smoke() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        ctx = ExecutionContext(
            request_id="req-1",
            provider_id="provider-1",
            model="test-model",
            trace_spans=(
                SpanItem(
                    span_id="span-1",
                    parent_id="",
                    name="root",
                    kind="internal",
                    status="ok",
                    duration_ms=1.5,
                ),
                SpanItem(
                    span_id="span-2",
                    parent_id="span-1",
                    name="child",
                    kind="tool",
                    status="ok",
                    duration_ms=0.5,
                ),
            ),
            artifacts=(
                ArtifactItem(
                    artifact_id="art-1",
                    kind="text",
                    label="Result",
                    size_bytes=128,
                ),
            ),
            metrics={"latency_ms": 3.2, "tokens": 42},
        )

        inspector = ExecutionInspector(root)
        inspector.pack(fill="both", expand=True)
        inspector.update_context(ctx)
        root.update_idletasks()

        assert isinstance(inspector.trace_section, CollapsibleSection)
        assert isinstance(inspector.provider_section, CollapsibleSection)
        assert isinstance(inspector.artifacts_section, CollapsibleSection)
        assert isinstance(inspector.metrics_section, CollapsibleSection)

        before = inspector.trace_section._expanded
        inspector.trace_section.toggle()
        assert inspector.trace_section._expanded is (not before)

        host = InspectorHost(root)
        host.pack(fill="both", expand=True)
        host.register("execution", inspector)
        host.set_default(inspector)
        host.clear()
        root.update_idletasks()

        assert host._visible_widget is inspector
    finally:
        root.destroy()
