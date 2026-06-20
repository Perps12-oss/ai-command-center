"""Canonical note contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Note:
    note_id: str
    title: str
    content: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    updated_at: datetime = field(default_factory=datetime.utcnow)
