"""Artifact renderer factory tests."""

from __future__ import annotations

from ai_command_center.domain.artifact import ArtifactType
from ai_command_center.ui.renderers.artifact_renderer_factory import ArtifactRendererFactory


def test_renderer_factory_preview_and_stub_kinds() -> None:
    assert ArtifactRendererFactory.normalize_kind("CODE") == ArtifactType.CODE.value
    assert ArtifactRendererFactory.is_stub_kind(ArtifactType.PDF.value)
    assert ArtifactRendererFactory.uses_monospace(ArtifactType.CODE.value)
    assert ArtifactRendererFactory.uses_text_preview(ArtifactType.MARKDOWN.value)
    assert (
        ArtifactRendererFactory.preview_content(kind="text", content="", label="Label")
        == "Label"
    )
    assert "PDF preview" in ArtifactRendererFactory.stub_message(ArtifactType.PDF.value)
