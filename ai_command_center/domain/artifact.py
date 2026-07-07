"""Artifact domain model for the ACC artifact stream UI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ArtifactType(str, Enum):
    """Canonical artifact kinds aligned with ArtifactCard icons."""

    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    PDF = "pdf"
    EMAIL = "email"
    CALENDAR = "calendar"
    DATA = "data"
    MARKDOWN = "markdown"

    @classmethod
    def coerce(cls, value: str | ArtifactType) -> ArtifactType:
        if isinstance(value, ArtifactType):
            return value
        text = str(value).strip().lower()
        for member in cls:
            if member.value == text:
                return member
        return cls.TEXT


@dataclass(frozen=True, slots=True)
class Artifact:
    """Immutable artifact record produced by executions."""

    artifact_id: str
    kind: ArtifactType
    label: str
    size_bytes: int = 0
    content_ref: str = ""
    execution_id: str = ""
    mime_type: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "kind": self.kind.value,
            "label": self.label,
            "size_bytes": self.size_bytes,
            "content_ref": self.content_ref,
            "execution_id": self.execution_id,
            "mime_type": self.mime_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Artifact:
        return cls(
            artifact_id=str(payload.get("artifact_id", "")),
            kind=ArtifactType.coerce(str(payload.get("kind", "text"))),
            label=str(payload.get("label", "")),
            size_bytes=int(payload.get("size_bytes", 0) or 0),
            content_ref=str(payload.get("content_ref", "")),
            execution_id=str(payload.get("execution_id", "")),
            mime_type=str(payload.get("mime_type", "")),
            created_at=float(payload.get("created_at", 0.0) or 0.0),
            updated_at=float(payload.get("updated_at", 0.0) or 0.0),
        )


__all__ = ["Artifact", "ArtifactType"]
