"""Platform detection utilities."""

from ai_command_center.platform.detector import (
    get_architecture,
    get_baseline_log_path,
    get_ram_mb,
    is_arm64,
    ollama_available,
    validate_ollama_arm64_native,
)

__all__ = [
    "get_architecture",
    "get_baseline_log_path",
    "get_ram_mb",
    "is_arm64",
    "ollama_available",
    "validate_ollama_arm64_native",
]
