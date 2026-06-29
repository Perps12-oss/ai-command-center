"""Versioned architecture contracts — bump only with explicit governance review.

Contracts locked at Phase 3D → 4 transition.

Version bump policy:
    1. Update constants and SUPPORTED_VERSIONS below.
    2. Update gate history in docs/ARCHITECTURE.md#gate-history.
    3. Run full phase regression suite (scripts/verify_contracts.py and all verify_phase*.py).
    4. Constitutional review required if consumer/producer ownership changes.

Gate: python scripts/verify_contracts.py

ContextBundle v1.1 (current):
    Producer: ContextManager.build_context() only
    Consumer: OllamaService.stream_chat() / .stream() / .chat()
    v1.0 remains in SUPPORTED_VERSIONS for backward compatibility.

command.routed v1.0:
    contract_version: "1.0"

tool.invoke / tool.result v1.0 (Phase 4B):
    Producer: ShellToolService (and future tool bridges)
    Consumer: ToolExecutorService — one invocation per event, no loops

OllamaService API v1.0: unchanged.
"""

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

SUPPORTED_VERSIONS: dict[str, tuple[str, ...]] = {
    "context_bundle": (CONTEXT_BUNDLE_VERSION_LEGACY, CONTEXT_BUNDLE_VERSION),
    "command_routed": (COMMAND_ROUTED_VERSION,),
    "ollama_service": (OLLAMA_SERVICE_API_VERSION,),
    "tool": (TOOL_CONTRACT_VERSION,),
}
