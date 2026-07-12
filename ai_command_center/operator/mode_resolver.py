"""ModeResolver — determines operator mode based on intent and context.

Reference: docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md Section 8.1
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from ai_command_center.operator.intent_resolver import Intent, IntentType

if TYPE_CHECKING:
    from ai_command_center.core.event_bus import EventBus


class OperatorMode(str, Enum):
    """Operator behavior modes.

    Each mode has distinct response contracts and behavior patterns.
    """

    CHAT = "chat"  # Conversational interaction
    COMMAND = "command"  # Task execution
    INVESTIGATION = "investigation"  # Research and analysis
    ARCHITECT = "architect"  # Design and planning


# Intent to mode mapping
_INTENT_MODE_MAP: dict[IntentType, OperatorMode] = {
    IntentType.CHAT: OperatorMode.CHAT,
    IntentType.COMMAND: OperatorMode.COMMAND,
    IntentType.INVESTIGATION: OperatorMode.INVESTIGATION,
    IntentType.ARCHITECT: OperatorMode.ARCHITECT,
    IntentType.MEMORY: OperatorMode.CHAT,  # Memory ops use chat interface
    IntentType.SETTINGS: OperatorMode.COMMAND,  # Settings use command interface
    IntentType.UNKNOWN: OperatorMode.CHAT,  # Default to chat
}


class ModeResolver:
    """Determines the appropriate operator mode based on intent and context."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    def resolve(
        self,
        intent: Intent,
        user_input: str,
        workspace_context: dict[str, Any] | None = None,
    ) -> OperatorMode:
        """Determine the operator mode for the given intent and context.

        Mode determination follows this priority:
        1. Explicit mode indicators in user input (highest)
        2. Context-based overrides (overrides intent for CHAT)
        3. Intent-based mapping
        4. Default to CHAT
        """
        # Priority 1: Check for explicit mode indicators
        explicit_mode = self._detect_explicit_mode(user_input)
        if explicit_mode:
            return explicit_mode

        # Priority 2: Context-based overrides
        # Context can override default CHAT behavior
        if workspace_context:
            override = self._detect_context_override(workspace_context)
            if override:
                # Only override if intent would default to CHAT
                default_mode = _INTENT_MODE_MAP.get(intent.intent_type)
                if default_mode == OperatorMode.CHAT:
                    return override

        # Priority 3: Intent-based mapping
        mode = _INTENT_MODE_MAP.get(intent.intent_type)
        if mode:
            return mode

        # Priority 4: Default
        return OperatorMode.CHAT

    def _detect_explicit_mode(self, user_input: str) -> OperatorMode | None:
        """Check for explicit mode indicators in user input."""
        user_input_lower = user_input.lower()

        # Explicit investigation indicators
        if any(
            phrase in user_input_lower
            for phrase in [
                "investigate",
                "analyze this",
                "what does",
                "why is",
                "how does",
                "find all",
                "trace",
            ]
        ):
            return OperatorMode.INVESTIGATION

        # Explicit architect indicators
        if any(
            phrase in user_input_lower
            for phrase in [
                "design",
                "architect",
                "propose",
                "outline",
                "plan for",
            ]
        ):
            return OperatorMode.ARCHITECT

        # Explicit command indicators
        if any(
            phrase in user_input_lower
            for phrase in [
                "do this",
                "execute",
                "run command",
                "build it",
                "make it",
            ]
        ):
            return OperatorMode.COMMAND

        return None

    def _detect_context_override(
        self,
        workspace_context: dict[str, Any],
    ) -> OperatorMode | None:
        """Detect mode overrides based on workspace context."""
        # If we're in a code review context, prefer investigation
        if workspace_context.get("context_type") == "code_review":
            return OperatorMode.INVESTIGATION

        # If we're in a design document, prefer architect
        if workspace_context.get("context_type") == "design":
            return OperatorMode.ARCHITECT

        return None

    def get_mode_contract(self, mode: OperatorMode) -> str:
        """Return the response contract name for the given mode."""
        return {
            OperatorMode.CHAT: "ChatResponse",
            OperatorMode.COMMAND: "CommandResponse",
            OperatorMode.INVESTIGATION: "InvestigationResponse",
            OperatorMode.ARCHITECT: "ArchitectResponse",
        }.get(mode, "ChatResponse")


__all__ = [
    "ModeResolver",
    "OperatorMode",
]
