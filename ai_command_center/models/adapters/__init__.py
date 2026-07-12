"""Model adapters for different providers.

Reference: docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md Section 8.3
"""

from ai_command_center.models.adapters.ollama_adapter import OllamaAdapter
from ai_command_center.models.adapters.openai_adapter import OpenAIAdapter
from ai_command_center.models.adapters.anthropic_adapter import AnthropicAdapter

__all__ = [
    "AnthropicAdapter",
    "OpenAIAdapter",
    "OllamaAdapter",
]
