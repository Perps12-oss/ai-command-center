"""Tests for PlatformService and platform implementations."""

import pytest

from ai_command_center.platform.platform_service import (
    MacOSPlatformService,
    NotificationData,
    PlatformService,
    TrayIcon,
    WindowsPlatformService,
    LinuxPlatformService,
    get_platform_service,
)


class TestNotificationData:
    """Tests for NotificationData."""

    def test_create_notification(self):
        """Notifications can be created with required fields."""
        notification = NotificationData(
            title="Test Title",
            body="Test body message",
        )
        assert notification.title == "Test Title"
        assert notification.body == "Test body message"
        assert notification.icon == TrayIcon.NORMAL

    def test_notification_with_callback(self):
        """Notifications can include action callbacks."""
        callback_called = False

        def callback():
            nonlocal callback_called
            callback_called = True

        notification = NotificationData(
            title="Test",
            body="Body",
            action_callback=callback,
        )
        assert notification.action_callback is callback


class TestTrayIcon:
    """Tests for TrayIcon enum."""

    def test_tray_icon_values(self):
        """TrayIcon has expected values."""
        assert TrayIcon.NORMAL.value == "normal"
        assert TrayIcon.NOTIFICATION.value == "notification"
        assert TrayIcon.BUSY.value == "busy"
        assert TrayIcon.ERROR.value == "error"


class TestPlatformServiceABC:
    """Tests for PlatformService abstract base class."""

    def test_platform_services_have_properties(self):
        """Each platform service has required properties."""
        windows = WindowsPlatformService()
        assert windows.platform_name == "windows"

        linux = LinuxPlatformService()
        assert linux.platform_name == "linux"

        macos = MacOSPlatformService()
        assert macos.platform_name == "darwin"

    def test_platform_services_not_supported_on_wrong_platform(self):
        """Platform services report unsupported on wrong platform."""
        import sys

        original_platform = sys.platform

        try:
            # Test Windows service
            sys.platform = "linux"
            windows = WindowsPlatformService()
            assert windows.is_supported is False

            # Test Linux service
            sys.platform = "win32"
            linux = LinuxPlatformService()
            assert linux.is_supported is False

            # Test macOS service
            sys.platform = "linux"
            macos = MacOSPlatformService()
            assert macos.is_supported is False

        finally:
            sys.platform = original_platform


class TestGetPlatformService:
    """Tests for get_platform_service factory function."""

    def test_get_platform_service_returns_correct_type(self):
        """get_platform_service returns appropriate service for platform."""
        import sys

        original_platform = sys.platform

        try:
            sys.platform = "win32"
            service = get_platform_service()
            assert isinstance(service, WindowsPlatformService)

            sys.platform = "linux"
            service = get_platform_service()
            assert isinstance(service, LinuxPlatformService)

            sys.platform = "darwin"
            service = get_platform_service()
            assert isinstance(service, MacOSPlatformService)

        finally:
            sys.platform = original_platform
