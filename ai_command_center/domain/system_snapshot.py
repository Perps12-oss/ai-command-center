"""Canonical system snapshot contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SystemSnapshot:
    phase: str = "idle"
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ollama_online: bool = False
    service_states: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    tool_count: int = 0
    recent_commands: tuple[str, ...] = field(default_factory=tuple)
    event_rate: float = 0.0
    uptime: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)
