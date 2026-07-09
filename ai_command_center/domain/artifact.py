"""Canonical artifact contract for the Artifact System (ACC UI Refurbishment PR 6)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ArtifactType(StrEnum):
    """Supported artifact preview kinds."""

    TEXT = "text"
    CODE = "code"
    MARKDOWN = "markdown"
    IMAGE = "image"
    PDF = "pdf"
    EMAIL = "email"
    CALENDAR = "calendar"
    DATA = "data"


@dataclass(frozen=True, slots=True)
class Artifact:
    """Immutable artifact record — runtime domain contract."""

    artifact_id: str
    kind: str
    label: str
    content: str = ""
    size_bytes: int = 0
    mime_type: str = ""
    request_id: str = ""
    workspace_id: str = ""
    entity_id: str = ""
    source: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0

    def normalized_kind(self) -> str:
        raw = str(self.kind or ArtifactType.TEXT).strip().lower()
        if raw in {t.value for t in ArtifactType}:
            return raw
        return ArtifactType.TEXT.value

    def to_bus_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "kind": self.normalized_kind(),
            "label": self.label,
            "content": self.content,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
            "request_id": self.request_id,
            "workspace_id": self.workspace_id,
            "entity_id": self.entity_id,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_bus_payload(cls, payload: dict[str, Any]) -> Artifact:
        return cls(
            artifact_id=str(payload.get("artifact_id", "")).strip(),
            kind=str(payload.get("kind", ArtifactType.TEXT)).strip() or ArtifactType.TEXT,
            label=str(payload.get("label", "")).strip(),
            content=str(payload.get("content", "")),
            size_bytes=int(payload.get("size_bytes", 0) or 0),
            mime_type=str(payload.get("mime_type", "")).strip(),
            request_id=str(payload.get("request_id", "")).strip(),
            workspace_id=str(payload.get("workspace_id", "")).strip(),
            entity_id=str(payload.get("entity_id", "")).strip(),
            source=str(payload.get("source", "")).strip(),
            created_at=float(payload.get("created_at", 0.0) or 0.0),
            updated_at=float(payload.get("updated_at", 0.0) or 0.0),
        )


def infer_tool_artifact_kind(tool_name: str) -> str:
    """Map tool identifiers to artifact preview kinds."""
    name = tool_name.strip().lower()
    if name in {"shell", "run_shell", "execute_shell"}:
        return ArtifactType.CODE.value
    if "note" in name or "markdown" in name:
        return ArtifactType.MARKDOWN.value
    return ArtifactType.TEXT.value


def infer_chat_artifact_kind(text: str) -> str:
    """Heuristic kind for assistant chat output."""
    stripped = text.lstrip()
    if stripped.startswith("#") or "\n# " in text or "```" in text:
        return ArtifactType.MARKDOWN.value
    return ArtifactType.TEXT.value


__all__ = [
    "Artifact",
    "ArtifactType",
    "infer_chat_artifact_kind",
    "infer_tool_artifact_kind",
]
