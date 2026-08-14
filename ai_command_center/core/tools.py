"""Tool contracts — single-step execution only (Phase 4B)."""

from __future__ import annotations

from ai_command_center.domain.runtime_safety import SecurityTier

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
    # ADR-004 classification. When None the authoritative table in
    # ``core.security_policy`` is consulted; if neither declares a tier the
    # action is rejected rather than defaulted.
    tier: SecurityTier | None = None


@dataclass(frozen=True, slots=True)
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    facts: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "contract_version": TOOL_CONTRACT_VERSION,
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }
        if self.facts:
            payload["facts"] = dict(self.facts)
        return payload
