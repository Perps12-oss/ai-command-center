"""Provider execution result contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ProviderExecutionResult:
    success: bool
    response_text: str = ""
    facts: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
