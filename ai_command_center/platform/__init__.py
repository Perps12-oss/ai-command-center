"""Platform detection utilities."""

from ai_command_center.platform.detector import (
    get_architecture,
    get_ram_mb,
    is_arm64,
    ollama_available,
)

__all__ = [
    "get_architecture",
    "get_ram_mb",
    "is_arm64",
    "ollama_available",
]
