"""Versioned architecture contracts — bump only with explicit governance review."""

from __future__ import annotations

# ContextBundle (ContextManager → OllamaService)
CONTEXT_BUNDLE_VERSION = "1.1"
CONTEXT_BUNDLE_VERSION_LEGACY = "1.0"

# command.routed envelope (CommandRouter → handlers)
COMMAND_ROUTED_VERSION = "1.0"

# OllamaService public API surface
OLLAMA_SERVICE_API_VERSION = "1.0"

# tool.invoke / tool.result envelope (Phase 4B)
TOOL_CONTRACT_VERSION = "1.0"

# workspace.resolved envelope (WorkspaceService -> AppState/UI, v3.5 runtime wiring)
WORKSPACE_RESOLVED_VERSION = "1.0"

SUPPORTED_VERSIONS: dict[str, tuple[str, ...]] = {
    "context_bundle": (CONTEXT_BUNDLE_VERSION_LEGACY, CONTEXT_BUNDLE_VERSION),
    "command_routed": (COMMAND_ROUTED_VERSION,),
    "ollama_service": (OLLAMA_SERVICE_API_VERSION,),
    "tool": (TOOL_CONTRACT_VERSION,),
    "workspace_resolved": (WORKSPACE_RESOLVED_VERSION,),
}
