"""Versioned architecture contracts — bump only with explicit governance review."""

from __future__ import annotations

# ContextBundle (ContextManager → OllamaService)
CONTEXT_BUNDLE_VERSION = "1.0"

# command.routed envelope (CommandRouter → handlers)
COMMAND_ROUTED_VERSION = "1.0"

# OllamaService public API surface
OLLAMA_SERVICE_API_VERSION = "1.0"

SUPPORTED_VERSIONS: dict[str, tuple[str, ...]] = {
    "context_bundle": (CONTEXT_BUNDLE_VERSION,),
    "command_routed": (COMMAND_ROUTED_VERSION,),
    "ollama_service": (OLLAMA_SERVICE_API_VERSION,),
}
