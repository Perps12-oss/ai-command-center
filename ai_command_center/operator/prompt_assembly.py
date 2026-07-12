"""PromptAssemblyService — layered prompt composition for operator.

Reference: docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md Section 8.2
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.operator.mode_resolver import OperatorMode
    from ai_command_center.operator.intent_resolver import Intent


# Base rules that apply to all modes
_BASE_RULES = """You are an AI Command Center operator. Your role is to assist users with:
- Task execution and automation
- Code analysis and debugging
- Research and investigation
- Design and planning

CRITICAL RULES:
1. Always provide evidence for claims
2. Never claim capabilities you don't have
3. Verify external URLs before referencing them
4. Flag high-risk operations for user approval
5. Maintain context across the conversation
"""


# Mode-specific rules
_MODE_RULES: dict[str, str] = {
    "chat": """
CHAT MODE RULES:
- Respond naturally to questions
- Provide clear explanations
- Include code examples when relevant
- Suggest related actions when helpful
""",
    "command": """
COMMAND MODE RULES:
- Provide specific, actionable commands
- Explain what each command does
- List all side effects
- Include rollback instructions for destructive operations
- Always require user confirmation for destructive commands
""",
    "investigation": """
INVESTIGATION MODE RULES:
- Structure findings clearly
- Provide evidence for each finding
- Include confidence levels
- Make recommendations based on evidence
- Cite sources when available
""",
    "architect": """
ARCHITECT MODE RULES:
- Present clear designs with rationale
- Consider alternatives and tradeoffs
- Identify risks and mitigations
- Estimate effort and complexity
- Make implementation recommendations
""",
}


class PromptAssemblyService:
    """Builds prompts dynamically in layers.

    Layer composition:
    1. BASE_RULES - Core operator identity and rules
    2. MODE_RULES - Mode-specific behavior
    3. WORKSPACE_STATE - Current context
    4. PROVIDER_STATE - Available capabilities
    5. EVIDENCE - Supporting information
    6. USER_REQUEST - The actual user input
    """

    def __init__(
        self,
        bus: EventBus,
        mode_resolver: Any = None,
    ) -> None:
        self._bus = bus
        self._mode_resolver = mode_resolver

    def assemble(
        self,
        mode: OperatorMode,
        intent: Intent,
        user_input: str,
        workspace_context: dict[str, Any] | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        evidence: list[str] | None = None,
    ) -> str:
        """Assemble a complete prompt from layers.

        Args:
            mode: The current operator mode
            intent: Classified user intent
            user_input: The user's request
            workspace_context: Current workspace state
            conversation_history: Recent conversation
            evidence: Supporting information/prior findings

        Returns:
            Assembled prompt string ready for model inference
        """
        layers: list[str] = []

        # Layer 1: Base rules
        layers.append(_BASE_RULES)

        # Layer 2: Mode-specific rules
        mode_rules = _MODE_RULES.get(mode.value, "")
        if mode_rules:
            layers.append(mode_rules)

        # Layer 3: Workspace state
        if workspace_context:
            workspace_layer = self._assemble_workspace_layer(workspace_context)
            layers.append(workspace_layer)

        # Layer 4: Conversation history (last 5 turns)
        if conversation_history:
            history_layer = self._assemble_history_layer(conversation_history)
            layers.append(history_layer)

        # Layer 5: Evidence
        if evidence:
            evidence_layer = self._assemble_evidence_layer(evidence)
            layers.append(evidence_layer)

        # Layer 6: User request
        layers.append(f"USER REQUEST:\n{user_input}")

        return "\n\n".join(layers)

    def _assemble_workspace_layer(
        self,
        context: dict[str, Any],
    ) -> str:
        """Assemble workspace state layer."""
        lines = ["WORKSPACE STATE:"]

        # Add relevant context fields
        relevant_fields = ["workspace_name", "workspace_path", "context_type", "active_file"]
        for field in relevant_fields:
            if field in context:
                lines.append(f"  {field}: {context[field]}")

        # Add any additional metadata
        if "metadata" in context:
            lines.append("  metadata:")
            for key, value in context["metadata"].items():
                lines.append(f"    {key}: {value}")

        return "\n".join(lines)

    def _assemble_history_layer(
        self,
        history: list[dict[str, str]],
    ) -> str:
        """Assemble conversation history layer (last 5 turns)."""
        lines = ["CONVERSATION HISTORY:"]

        # Take last 5 turns
        recent = history[-5:] if len(history) > 5 else history

        for i, turn in enumerate(recent):
            role = turn.get("role", "unknown")
            content = turn.get("content", "")[:500]  # Truncate long messages
            lines.append(f"  [{role}]: {content}")

        return "\n".join(lines)

    def _assemble_evidence_layer(
        self,
        evidence: list[str],
    ) -> str:
        """Assemble evidence layer."""
        lines = ["EVIDENCE:"]

        for i, item in enumerate(evidence, 1):
            lines.append(f"  {i}. {item}")

        return "\n".join(lines)


__all__ = [
    "PromptAssemblyService",
]
