"""Canonical tool execution contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolExecution:
    tool_name: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    status: str = "pending"
    inputs: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    outputs: tuple[Any, ...] = field(default_factory=tuple)
    error: str | None = None
