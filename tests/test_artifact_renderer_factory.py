"""Artifact renderer factory tests."""

from __future__ import annotations

from ai_command_center.domain.artifact import ArtifactType
from ai_command_center.ui.renderers.artifact_renderer_factory import ArtifactRendererFactory


def test_renderer_factory_preview_and_unsupported_kinds() -> None:
    assert ArtifactRendererFactory.normalize_kind("CODE") == ArtifactType.CODE.value
    assert ArtifactRendererFactory.is_unsupported_kind(ArtifactType.PDF.value)
    assert ArtifactRendererFactory.uses_monospace(ArtifactType.CODE.value)
    assert ArtifactRendererFactory.uses_text_preview(ArtifactType.MARKDOWN.value)
    assert (
        ArtifactRendererFactory.preview_content(kind="text", content="", label="Label")
        == "Label"
    )
    msg = ArtifactRendererFactory.unsupported_message(ArtifactType.PDF.value)
    assert "Unsupported artifact type: pdf" in msg
    assert "no renderer registered" in msg
