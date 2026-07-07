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
                "kind": "decision",
                "ref_id": "dec-1",
                "label": "Decision One",
                "payload": {"decision_id": "dec-1"},
            }
        )
        host.show(unknown_ref)
        root.update_idletasks()
        assert host._visible_widget is host._placeholder
    finally:
        root.destroy()
