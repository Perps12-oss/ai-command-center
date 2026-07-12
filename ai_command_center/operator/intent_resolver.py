"""IntentResolver — classifies user intent from natural language input.

Reference: docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md Section 8.1
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_command_center.core.event_bus import EventBus


class IntentType(str, Enum):
    """High-level intent categories."""

    CHAT = "chat"  # General conversation or questions
    COMMAND = "command"  # Request to execute a specific action
    INVESTIGATION = "investigation"  # Research or analysis request
    ARCHITECT = "architect"  # Design or planning request
    MEMORY = "memory"  # Memory/recall operations
    SETTINGS = "settings"  # Configuration changes
    UNKNOWN = "unknown"  # Unclassifiable


@dataclass
class Intent:
    """Resolved intent with confidence and metadata."""

    intent_type: IntentType
    confidence: float  # 0.0 - 1.0
    entities: dict[str, Any] | None = None
    modifiers: list[str] | None = None
    raw_query: str | None = None


# Intent classification patterns
_INTENT_PATTERNS: dict[IntentType, list[str]] = {
    IntentType.COMMAND: [
        "run",
        "execute",
        "do",
        "make",
        "create",
        "delete",
        "remove",
        "update",
        "edit",
        "fix",
        "build",
        "install",
        "deploy",
        "start",
        "stop",
    ],
    IntentType.INVESTIGATION: [
        "find",
        "search",
        "analyze",
        "investigate",
        "examine",
        "check",
        "review",
        "audit",
        "trace",
        "debug",
        "diagnose",
    ],
    IntentType.ARCHITECT: [
        "design",
        "architect",
        "plan",
        "propose",
        "suggest",
        "recommend",
        "outline",
        "sketch",
        "structure",
    ],
    IntentType.MEMORY: [
        "remember",
        "recall",
        "forget",
        "store",
        "save",
        "note",
        "remember that",
        "remind me",
    ],
    IntentType.SETTINGS: [
        "configure",
        "set",
        "change",
        "adjust",
        "enable",
        "disable",
        "toggle",
        "preference",
    ],
    IntentType.CHAT: [],  # Default fallback
}


class IntentResolver:
    """Classifies user intent from natural language input."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    def resolve(
        self,
        user_input: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> Intent:
        """Classify the user's intent from their input.

        Uses keyword matching as a first pass. In production, this could
        delegate to a lightweight model for better accuracy.
        """
        user_input_lower = user_input.lower().strip()

        # Check each intent type's patterns
        scores: dict[IntentType, float] = {}

        for intent_type, keywords in _INTENT_PATTERNS.items():
            if not keywords:
                continue

            matches = sum(1 for kw in keywords if kw in user_input_lower)
            if matches > 0:
                # Normalize by input length to avoid bias toward longer inputs
                score = min(matches / len(keywords), 1.0)
                scores[intent_type] = score

        if scores:
            # Pick the highest-scoring intent
            best_intent = max(scores, key=scores.get)
            confidence = scores[best_intent]
        else:
            # Default to chat for unrecognized inputs
            best_intent = IntentType.CHAT
            confidence = 0.5

        # Extract entities based on intent type
        entities = self._extract_entities(user_input, best_intent)

        return Intent(
            intent_type=best_intent,
            confidence=confidence,
            entities=entities,
            raw_query=user_input,
        )

    def _extract_entities(
        self,
        user_input: str,
        intent: IntentType,
    ) -> dict[str, Any]:
        """Extract relevant entities from the input based on intent type."""
        entities: dict[str, Any] = {}

        # Simple entity extraction - in production, use NER
        words = user_input.split()

        # Extract quoted strings
        import re

        quoted = re.findall(r'"([^"]*)"', user_input)
        if quoted:
            entities["quoted_strings"] = quoted

        # Extract code-like patterns
        code_patterns = re.findall(r"`([^`]+)`", user_input)
        if code_patterns:
            entities["code_snippets"] = code_patterns

        # Extract paths
        paths = re.findall(r"[\w/\\]+\.[\w]+", user_input)
        if paths:
            entities["potential_paths"] = paths

        # Extract command-like patterns for COMMAND intent
        if intent == IntentType.COMMAND:
            first_word = words[0] if words else ""
            if first_word.lower() in ["run", "execute", "do"]:
                entities["action_verb"] = first_word.lower()

        return entities


__all__ = [
    "Intent",
    "IntentResolver",
    "IntentType",
]
