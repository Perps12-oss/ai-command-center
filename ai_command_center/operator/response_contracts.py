"""Response contracts — structured response schemas for each operator mode.

Reference: docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md Section 8.4
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ai_command_center.operator.mode_resolver import OperatorMode


class ResponseContract(ABC):
    """Base class for all response contracts."""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""

    @abstractmethod
    def validate(self) -> list[str]:
        """Validate the response structure. Returns list of errors."""


@dataclass
class Artifact:
    """A rendered artifact (code, markdown, etc.)."""

    kind: str  # e.g., "code", "markdown", "chart"
    content: str
    language: str | None = None
    filename: str | None = None


@dataclass
class Suggestion:
    """A suggested follow-up action."""

    label: str
    description: str | None = None


@dataclass
class ChatResponse(ResponseContract):
    """Response contract for chat mode."""

    message: str
    artifacts: list[Artifact] = field(default_factory=list)
    suggestions: list[Suggestion] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "chat",
            "message": self.message,
            "artifacts": [
                {
                    "kind": a.kind,
                    "content": a.content,
                    "language": a.language,
                    "filename": a.filename,
                }
                for a in self.artifacts
            ],
            "suggestions": [
                {"label": s.label, "description": s.description}
                for s in self.suggestions
            ],
        }

    def validate(self) -> list[str]:
        errors = []
        if not self.message:
            errors.append("message is required")
        if not isinstance(self.artifacts, list):
            errors.append("artifacts must be a list")
        if not isinstance(self.suggestions, list):
            errors.append("suggestions must be a list")
        return errors


@dataclass
class CommandResponse(ResponseContract):
    """Response contract for command mode."""

    command: str  # Primary command to execute
    explanation: str | None = None
    confirm_required: bool = True
    dry_run: bool = False
    side_effects: list[str] = field(default_factory=list)
    rollback_plan: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "command",
            "command": self.command,
            "explanation": self.explanation,
            "confirm_required": self.confirm_required,
            "dry_run": self.dry_run,
            "side_effects": self.side_effects,
            "rollback_plan": self.rollback_plan,
        }

    def validate(self) -> list[str]:
        errors = []
        if not self.command:
            errors.append("command is required")
        if self.confirm_required and not self.explanation:
            errors.append("explanation required when confirm_required is True")
        return errors


@dataclass
class InvestigationResponse(ResponseContract):
    """Response contract for investigation mode."""

    findings: list[str]
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5  # 0.0 - 1.0
    summary: str | None = None
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "investigation",
            "findings": self.findings,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "summary": self.summary,
            "recommendations": self.recommendations,
        }

    def validate(self) -> list[str]:
        errors = []
        if not self.findings:
            errors.append("findings must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            errors.append("confidence must be between 0.0 and 1.0")
        return errors


@dataclass
class ArchitectResponse(ResponseContract):
    """Response contract for architect mode."""

    design: str  # Primary design/plan
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    tradeoffs: list[dict[str, str]] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    estimated_effort: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "architect",
            "design": self.design,
            "alternatives": self.alternatives,
            "tradeoffs": self.tradeoffs,
            "risks": self.risks,
            "estimated_effort": self.estimated_effort,
        }

    def validate(self) -> list[str]:
        errors = []
        if not self.design:
            errors.append("design is required")
        return errors


def create_response(
    mode: OperatorMode,
    content: str,
    **kwargs: Any,
) -> ResponseContract:
    """Factory function to create a response of the appropriate type."""
    # Build appropriate kwargs based on mode
    if mode == OperatorMode.CHAT:
        return ChatResponse(message=content, **kwargs)
    elif mode == OperatorMode.COMMAND:
        return CommandResponse(command=content, **kwargs)
    elif mode == OperatorMode.INVESTIGATION:
        return InvestigationResponse(findings=[content], **kwargs)
    elif mode == OperatorMode.ARCHITECT:
        return ArchitectResponse(design=content, **kwargs)
    else:
        return ChatResponse(message=content)


__all__ = [
    "ArchitectResponse",
    "Artifact",
    "ChatResponse",
    "CommandResponse",
    "create_response",
    "InvestigationResponse",
    "ResponseContract",
    "Suggestion",
]
