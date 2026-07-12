"""PlatformService ABC — unified cross-platform abstraction.

Reference: docs/plans/PHASE_11_CROSS_PLATFORM_PLAN.md Section 11.3
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class TrayIcon(Enum):
    """System tray icon states."""

    NORMAL = "normal"
    NOTIFICATION = "notification"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class NotificationData:
    """Data for a system notification."""

    title: str
    body: str
    icon: TrayIcon = TrayIcon.NORMAL
    action_callback: Callable[[], None] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PlatformService(ABC):
    """Abstract base class for platform-specific functionality.

    PlatformService provides a unified interface for:
    - System tray management
    - Global hotkeys
    - Notifications
    - Window management
    - Platform detection

    Each platform (Windows, macOS, Linux) provides a concrete implementation.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name (e.g., 'windows', 'darwin', 'linux')."""
        pass

    @property
    @abstractmethod
    def is_supported(self) -> bool:
        """Return True if this platform is fully supported."""
        pass

    # ============ System Tray ============

    @abstractmethod
    def setup_tray(
        self,
        icon_path: str | None = None,
        tooltip: str = "AI Command Center",
    ) -> bool:
        """Setup the system tray icon.

        Args:
            icon_path: Path to the tray icon image
            tooltip: Tooltip text for the tray icon

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def show_tray(self) -> bool:
        """Show the system tray icon."""
        pass

    @abstractmethod
    def hide_tray(self) -> bool:
        """Hide the system tray icon."""
        pass

    @abstractmethod
    def update_tray_icon(self, icon: TrayIcon) -> bool:
        """Update the tray icon to a new state.

        Args:
            icon: The new tray icon state

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def set_tray_tooltip(self, tooltip: str) -> bool:
        """Set the tray icon tooltip text.

        Args:
            tooltip: New tooltip text

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def destroy_tray(self) -> None:
        """Destroy the system tray icon."""
        pass

    # ============ Notifications ============

    @abstractmethod
    def show_notification(self, notification: NotificationData) -> bool:
        """Show a system notification.

        Args:
            notification: Notification data

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def clear_notifications(self) -> None:
        """Clear all pending notifications."""
        pass

    # ============ Window Management ============

    @abstractmethod
    def show_window(self) -> bool:
        """Bring the main window to the foreground."""
        pass

    @abstractmethod
    def hide_window(self) -> bool:
        """Hide the main window."""
        pass

    @abstractmethod
    def toggle_window(self) -> bool:
        """Toggle window visibility."""
        pass

    @abstractmethod
    def is_window_visible(self) -> bool:
        """Return True if the main window is visible."""
        pass

    # ============ Clipboard ============

    @abstractmethod
    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text to the system clipboard.

        Args:
            text: Text to copy

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def get_from_clipboard(self) -> str | None:
        """Get text from the system clipboard.

        Returns:
            Clipboard text, or None if empty/unavailable
        """
        pass

    # ============ File Operations ============

    @abstractmethod
    def reveal_in_explorer(self, path: str) -> bool:
        """Reveal a file/folder in the system file explorer.

        Args:
            path: Path to reveal

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def open_in_terminal(self, path: str) -> bool:
        """Open a folder in the system terminal.

        Args:
            path: Path to open

        Returns:
            True if successful
        """
        pass

    # ============ Power Management ============

    @abstractmethod
    def is_on_battery(self) -> bool:
        """Return True if the system is running on battery."""
        pass

    @abstractmethod
    def request_background_time(self, seconds: int) -> bool:
        """Request background execution time.

        Args:
            seconds: Requested time in seconds

        Returns:
            True if the request was granted
        """
        pass


class WindowsPlatformService(PlatformService):
    """Windows-specific implementation of PlatformService."""

    @property
    def platform_name(self) -> str:
        return "windows"

    @property
    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def setup_tray(self, icon_path: str | None = None, tooltip: str = "AI Command Center") -> bool:
        # Windows implementation would use pystray or similar
        raise NotImplementedError("Windows tray not yet implemented")

    def show_tray(self) -> bool:
        raise NotImplementedError("Windows tray not yet implemented")

    def hide_tray(self) -> bool:
        raise NotImplementedError("Windows tray not yet implemented")

    def update_tray_icon(self, icon: TrayIcon) -> bool:
        raise NotImplementedError("Windows tray not yet implemented")

    def set_tray_tooltip(self, tooltip: str) -> bool:
        raise NotImplementedError("Windows tray not yet implemented")

    def destroy_tray(self) -> None:
        pass

    def show_notification(self, notification: NotificationData) -> bool:
        raise NotImplementedError("Windows notifications not yet implemented")

    def clear_notifications(self) -> None:
        pass

    def show_window(self) -> bool:
        raise NotImplementedError("Windows window management not yet implemented")

    def hide_window(self) -> bool:
        raise NotImplementedError("Windows window management not yet implemented")

    def toggle_window(self) -> bool:
        raise NotImplementedError("Windows window management not yet implemented")

    def is_window_visible(self) -> bool:
        raise NotImplementedError("Windows window management not yet implemented")

    def copy_to_clipboard(self, text: str) -> bool:
        raise NotImplementedError("Windows clipboard not yet implemented")

    def get_from_clipboard(self) -> str | None:
        raise NotImplementedError("Windows clipboard not yet implemented")

    def reveal_in_explorer(self, path: str) -> bool:
        raise NotImplementedError("Windows explorer integration not yet implemented")

    def open_in_terminal(self, path: str) -> bool:
        raise NotImplementedError("Windows terminal integration not yet implemented")

    def is_on_battery(self) -> bool:
        raise NotImplementedError("Windows power management not yet implemented")

    def request_background_time(self, seconds: int) -> bool:
        raise NotImplementedError("Windows background time not yet implemented")


class MacOSPlatformService(PlatformService):
    """macOS-specific implementation of PlatformService."""

    @property
    def platform_name(self) -> str:
        return "darwin"

    @property
    def is_supported(self) -> bool:
        return sys.platform == "darwin"

    def setup_tray(self, icon_path: str | None = None, tooltip: str = "AI Command Center") -> bool:
        # macOS implementation would use rumps or similar
        raise NotImplementedError("macOS tray not yet implemented")

    def show_tray(self) -> bool:
        raise NotImplementedError("macOS tray not yet implemented")

    def hide_tray(self) -> bool:
        raise NotImplementedError("macOS tray not yet implemented")

    def update_tray_icon(self, icon: TrayIcon) -> bool:
        raise NotImplementedError("macOS tray not yet implemented")

    def set_tray_tooltip(self, tooltip: str) -> bool:
        raise NotImplementedError("macOS tray not yet implemented")

    def destroy_tray(self) -> None:
        pass

    def show_notification(self, notification: NotificationData) -> bool:
        raise NotImplementedError("macOS notifications not yet implemented")

    def clear_notifications(self) -> None:
        pass

    def show_window(self) -> bool:
        raise NotImplementedError("macOS window management not yet implemented")

    def hide_window(self) -> bool:
        raise NotImplementedError("macOS window management not yet implemented")

    def toggle_window(self) -> bool:
        raise NotImplementedError("macOS window management not yet implemented")

    def is_window_visible(self) -> bool:
        raise NotImplementedError("macOS window management not yet implemented")

    def copy_to_clipboard(self, text: str) -> bool:
        raise NotImplementedError("macOS clipboard not yet implemented")

    def get_from_clipboard(self) -> str | None:
        raise NotImplementedError("macOS clipboard not yet implemented")

    def reveal_in_explorer(self, path: str) -> bool:
        raise NotImplementedError("macOS Finder integration not yet implemented")

    def open_in_terminal(self, path: str) -> bool:
        raise NotImplementedError("macOS terminal integration not yet implemented")

    def is_on_battery(self) -> bool:
        raise NotImplementedError("macOS power management not yet implemented")

    def request_background_time(self, seconds: int) -> bool:
        raise NotImplementedError("macOS background time not yet implemented")


class LinuxPlatformService(PlatformService):
    """Linux-specific implementation of PlatformService."""

    @property
    def platform_name(self) -> str:
        return "linux"

    @property
    def is_supported(self) -> bool:
        return sys.platform == "linux"

    def setup_tray(self, icon_path: str | None = None, tooltip: str = "AI Command Center") -> bool:
        # Linux implementation would use pystray or AppIndicator
        raise NotImplementedError("Linux tray not yet implemented")

    def show_tray(self) -> bool:
        raise NotImplementedError("Linux tray not yet implemented")

    def hide_tray(self) -> bool:
        raise NotImplementedError("Linux tray not yet implemented")

    def update_tray_icon(self, icon: TrayIcon) -> bool:
        raise NotImplementedError("Linux tray not yet implemented")

    def set_tray_tooltip(self, tooltip: str) -> bool:
        raise NotImplementedError("Linux tray not yet implemented")

    def destroy_tray(self) -> None:
        pass

    def show_notification(self, notification: NotificationData) -> bool:
        raise NotImplementedError("Linux notifications not yet implemented")

    def clear_notifications(self) -> None:
        pass

    def show_window(self) -> bool:
        raise NotImplementedError("Linux window management not yet implemented")

    def hide_window(self) -> bool:
        raise NotImplementedError("Linux window management not yet implemented")

    def toggle_window(self) -> bool:
        raise NotImplementedError("Linux window management not yet implemented")

    def is_window_visible(self) -> bool:
        raise NotImplementedError("Linux window management not yet implemented")

    def copy_to_clipboard(self, text: str) -> bool:
        raise NotImplementedError("Linux clipboard not yet implemented")

    def get_from_clipboard(self) -> str | None:
        raise NotImplementedError("Linux clipboard not yet implemented")

    def reveal_in_explorer(self, path: str) -> bool:
        raise NotImplementedError("Linux file manager integration not yet implemented")

    def open_in_terminal(self, path: str) -> bool:
        raise NotImplementedError("Linux terminal integration not yet implemented")

    def is_on_battery(self) -> bool:
        raise NotImplementedError("Linux power management not yet implemented")

    def request_background_time(self, seconds: int) -> bool:
        raise NotImplementedError("Linux background time not yet implemented")


def get_platform_service() -> PlatformService:
    """Get the appropriate PlatformService for the current platform."""
    if sys.platform == "win32":
        return WindowsPlatformService()
    if sys.platform == "darwin":
        return MacOSPlatformService()
    if sys.platform == "linux":
        return LinuxPlatformService()
    raise NotImplementedError(f"Platform {sys.platform} is not supported")


__all__ = [
    "NotificationData",
    "PlatformService",
    "TrayIcon",
    "get_platform_service",
]
