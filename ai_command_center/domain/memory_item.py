"""Canonical memory item contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MemoryItem:
    memory_id: str
    content: str
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=datetime.utcnow)
