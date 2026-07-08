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

from ai_command_center.domain.inspectable import InspectableRef
from ai_command_center.ui.components.inspector import (
    ArtifactInspector,
    InspectorHost,
    ProviderInspector,
)
from ai_command_center.ui.views.chat import message_block as chat_message_block


def test_artifact_and_provider_inspectors_smoke() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        artifact_ref = InspectableRef.from_payload(
            {
                "kind": "artifact",
                "ref_id": "art-1",
                "label": "Artifact One",
                "payload": {
                    "artifact_id": "art-1",
                    "kind": "text",
                    "label": "Artifact One",
                    "size_bytes": 128,
                    "content": "Artifact content preview",
                },
            }
        )
        provider_ref = InspectableRef.from_payload(
            {
                "kind": "provider",
                "ref_id": "prov-1",
                "label": "Provider One",
                "payload": {
                    "provider_id": "prov-1",
                    "model": "test-model",
                    "health_state": "healthy",
                    "latency_ms": 12.5,
                },
            }
        )

        artifact = ArtifactInspector(root)
        artifact.pack(fill="both", expand=True)
        artifact.update(artifact_ref)

        provider = ProviderInspector(root)
        provider.pack(fill="both", expand=True)
        provider.update(provider_ref)

        host = InspectorHost(root)
        host.pack(fill="both", expand=True)

        host.show(artifact_ref)
        root.update_idletasks()
        assert host._visible_widget is host._registry["artifact"]
        assert host._title.cget("text") == "Artifact One"

        host.show(provider_ref)
        root.update_idletasks()
        assert host._visible_widget is host._registry["provider"]
        assert host._title.cget("text") == "Provider One"

        unknown_ref = InspectableRef.from_payload(
            {
                "kind": "workflow",
                "ref_id": "wf-1",
                "label": "Workflow One",
                "payload": {"workflow_id": "wf-1"},
            }
        )
        host.show(unknown_ref)
        root.update_idletasks()
        assert host._visible_widget is host._placeholder
    finally:
        root.destroy()


def test_assistant_message_text_widget_is_not_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tk.Tk()
    root.withdraw()
    captured: list[tuple[object, ...]] = []

    def record_bind(widgets, *, get_ref, on_select, on_navigate):
        captured.append(tuple(widgets))

    monkeypatch.setattr(chat_message_block, "bind_inspect_gestures", record_bind)

    try:
        ref = InspectableRef.from_payload(
            {
                "kind": "message",
                "ref_id": "msg-1",
                "label": "Assistant",
                "payload": {"role": "assistant", "content": "hello"},
            }
        )
        block = chat_message_block.AssistantMessageBlock(
            root,
            inspect_ref=ref,
            on_inspect_select=lambda _ref: None,
            on_inspect_navigate=lambda _ref: None,
        )
        block.pack(fill="both", expand=True)
        root.update_idletasks()

        assert captured
        widgets = captured[-1]
        assert block._textbox not in widgets
        assert block._bubble in widgets
        assert block in widgets
    finally:
        root.destroy()
