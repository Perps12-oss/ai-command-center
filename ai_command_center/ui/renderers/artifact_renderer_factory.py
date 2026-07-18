"""Artifact preview renderers (ACC UI Refurbishment PR 7).

Artifact preview kinds:
- Live preview: text, code, markdown, data
- Unsupported (no renderer registered): pdf, image, email, calendar
"""

from __future__ import annotations

from ai_command_center.domain.artifact import ArtifactType

_UNSUPPORTED_MESSAGES: dict[str, str] = {
    ArtifactType.PDF.value: (
        "Unsupported artifact type: pdf — no renderer registered.\n\n"
        "Install a PDF preview plugin to view documents, or export and open externally."
    ),
    ArtifactType.IMAGE.value: (
        "Unsupported artifact type: image — no renderer registered.\n\n"
        "Images can be exported and viewed in external applications."
    ),
    ArtifactType.CALENDAR.value: (
        "Unsupported artifact type: calendar — no renderer registered.\n\n"
        "Calendar events are not displayed in this build."
    ),
    ArtifactType.EMAIL.value: (
        "Unsupported artifact type: email — no renderer registered.\n\n"
        "Email content is not displayed in this build."
    ),
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
    def is_unsupported_kind(cls, kind: str) -> bool:
        return cls.normalize_kind(kind) in _UNSUPPORTED_MESSAGES

    @classmethod
    def unsupported_message(cls, kind: str) -> str:
        normalized = cls.normalize_kind(kind)
        return _UNSUPPORTED_MESSAGES.get(
            normalized,
            f"Unsupported artifact type: {normalized} — no renderer registered.",
        )

    # Backward-compatible aliases
    is_stub_kind = is_unsupported_kind
    stub_message = unsupported_message

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
