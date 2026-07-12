"""Platform package — cross-platform abstractions.

This package provides platform-specific implementations for:
- Hotkey providers
- System tray
- Notifications
- File system operations
- Window management

Reference: docs/plans/PHASE_11_CROSS_PLATFORM_PLAN.md
"""

from ai_command_center.platform.detector import (
    find_ollama_executable,
    get_architecture,
    get_baseline_log_path,
    get_pe_machine_type,
    get_process_rss_mb,
    get_ram_mb,
    is_arm64,
    ollama_available,
    read_baseline_log,
    validate_ollama_arm64_native,
    write_baseline_log,
)
from ai_command_center.platform.hotkey_provider import (
    HotkeyProvider,
    get_hotkey_provider,
)
from ai_command_center.platform.platform_service import PlatformService

__all__ = [
    # Detector
    "find_ollama_executable",
    "get_architecture",
    "get_baseline_log_path",
    "get_pe_machine_type",
    "get_process_rss_mb",
    "get_ram_mb",
    "is_arm64",
    "ollama_available",
    "read_baseline_log",
    "validate_ollama_arm64_native",
    "write_baseline_log",
    # Hotkey
    "HotkeyProvider",
    "get_hotkey_provider",
    # Platform Service
    "PlatformService",
]
