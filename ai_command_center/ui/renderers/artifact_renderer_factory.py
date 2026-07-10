"""Artifact preview renderers (ACC UI Refurbishment PR 7).

Artifact preview kinds:
- Live preview: text, code, markdown, data
- Stub (planned): pdf, image, email, calendar

UI Refurbishment P3 Slice 1b: Updated stub messages with clearer status.
"""

from __future__ import annotations

from ai_command_center.domain.artifact import ArtifactType

_STUB_MESSAGES: dict[str, str] = {
    ArtifactType.PDF.value: "[PDF] Preview requires PDF renderer plugin.\n\nInstall a PDF preview plugin to view documents.",
    ArtifactType.IMAGE.value: "[IMAGE] Preview not available in this build.\n\nImages can be exported and viewed in external applications.",
    ArtifactType.CALENDAR.value: "[CALENDAR] Calendar viewer coming soon.\n\nCalendar events will be displayed in a timeline view.",
    ArtifactType.EMAIL.value: "[EMAIL] Email preview coming soon.\n\nEmail content will be displayed in threaded format.",
}


class ArtifactRendererFactory:
    """Select preview behavior for artifact kinds without UI importing services."""

    @staticmethod
    def normalize_kind(kind: str) -> str:
        raw = str(kind or ArtifactType.TEXT).strip().lower()
        if raw in {t.value for t in ArtifactType}:
            return raw
        return ArtifactType.TEXT.value

    @classmethod
    def is_stub_kind(cls, kind: str) -> bool:
        return cls.normalize_kind(kind) in _STUB_MESSAGES

    @classmethod
    def stub_message(cls, kind: str) -> str:
        normalized = cls.normalize_kind(kind)
        return _STUB_MESSAGES.get(normalized, f"No preview for {normalized}")

    @classmethod
    def uses_monospace(cls, kind: str) -> bool:
        return cls.normalize_kind(kind) == ArtifactType.CODE.value

    @classmethod
    def uses_text_preview(cls, kind: str) -> bool:
        normalized = cls.normalize_kind(kind)
        return normalized in {
            ArtifactType.TEXT.value,
            ArtifactType.CODE.value,
            ArtifactType.MARKDOWN.value,
            ArtifactType.DATA.value,
        }

    @classmethod
    def preview_content(cls, *, kind: str, content: str, label: str = "") -> str:
        normalized = cls.normalize_kind(kind)
        body = content.strip()
        if body:
            return body
        if label.strip():
            return label
        return f"[{normalized} artifact]"


__all__ = ["ArtifactRendererFactory"]
