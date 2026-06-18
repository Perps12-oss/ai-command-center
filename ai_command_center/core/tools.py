"""Tool contracts — single-step execution only (Phase 4B)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ai_command_center.core.contracts import TOOL_CONTRACT_VERSION

ToolHandler = Callable[[dict[str, Any]], "ToolResult"]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    handler: ToolHandler


@dataclass(frozen=True, slots=True)
class ToolResult:
    success: bool
    output: str
    error: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "contract_version": TOOL_CONTRACT_VERSION,
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }
